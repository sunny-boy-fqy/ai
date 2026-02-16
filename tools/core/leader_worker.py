"""
AI CLI Leader-Worker 核心
实现 Leader AI 和 Worker AI 的协作机制

功能特性:
- API 调用自动重试
- 任务恢复（中断后可继续）
- 智能上下文管理
- 并发 Worker 执行
- 进度可视化
"""

import os
import sys
import json
import re
import asyncio
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
from contextlib import contextmanager
from ..config_mgr import ConfigManager
from ..plugin import PluginManager, MCPToolManager
from ..ui import UI
from .task_manager import TaskManager
from .input_handler import InputHandler

# 导入日志模块
from ..logger import debug, info, warn, error, api, task, set_log_level, DEBUG, INFO


@contextmanager
def suppress_stdout():
    """
    静默 stdout 输出的上下文管理器
    
    使用文件描述符级别的重定向，可以捕获子进程的输出
    """
    # 保存原始 stdout 文件描述符
    original_stdout_fd = os.dup(1)
    original_stdout = sys.stdout
    
    try:
        # 刷新缓冲区
        sys.stdout.flush()
        
        # 打开 /dev/null
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        
        # 重定向 stdout 到 /dev/null
        os.dup2(devnull_fd, 1)
        os.close(devnull_fd)
        
        # 更新 Python 的 sys.stdout
        sys.stdout = open(os.devnull, 'w')
        
        yield
    finally:
        # 刷新并恢复
        sys.stdout.flush()
        os.dup2(original_stdout_fd, 1)
        os.close(original_stdout_fd)
        sys.stdout = original_stdout


class MCPServerSuppressor:
    """MCP 服务器输出抑制器"""
    
    _instance = None
    _shown = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def show_startup_message(cls, servers: List[str]):
        """显示 MCP 服务器启动提示（只显示一次）"""
        if not cls._shown and servers:
            UI.info(f"MCP 管理器初始化完成，已加载 {len(servers)} 个插件")
            cls._shown = True


class ModelInterface:
    """模型接口 - 用于调用大模型（带重试机制）"""
    
    # 重试配置
    MAX_RETRIES = 3
    BASE_DELAY = 1.0
    MAX_DELAY = 30.0
    
    def __init__(self, config: Dict):
        self.config = config
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化客户端"""
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.config.get("api_key"),
                base_url=self.config.get("base_url")
            )
            debug(f"模型客户端初始化成功: {self.config.get('model')}")
        except ImportError:
            error("未安装 openai 库")
        except Exception as e:
            error(f"初始化客户端失败: {e}")
    
    def _should_retry(self, error: Exception) -> bool:
        """判断是否应该重试"""
        error_str = str(error).lower()
        retry_keywords = [
            'rate limit', '429', 'too many requests',
            'timeout', 'timed out', 'connection',
            'network', 'temporary', 'unavailable',
            'overloaded', 'capacity'
        ]
        return any(kw in error_str for kw in retry_keywords)
    
    def _calculate_delay(self, attempt: int) -> float:
        """计算重试延迟（指数退避 + 抖动）"""
        delay = min(self.BASE_DELAY * (2 ** attempt), self.MAX_DELAY)
        jitter = random.uniform(0.5, 1.5)
        return delay * jitter
    
    def call(
        self,
        prompt: str,
        system_prompt: str = None,
        tools: List[Dict] = None,
        stream: bool = False
    ) -> Tuple[str, List[Dict]]:
        """调用模型（带重试机制）"""
        if not self.client:
            return "客户端未初始化", []
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        last_error = None
        
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                kwargs = {
                    "model": self.config.get("model"),
                    "messages": messages,
                }
                if tools:
                    kwargs["tools"] = tools
                
                api(f"调用模型: {self.config.get('model')} (尝试 {attempt + 1})")
                
                response = self.client.chat.completions.create(**kwargs)
                
                content = response.choices[0].message.content or ""
                tool_calls = []
                
                if response.choices[0].message.tool_calls:
                    for tc in response.choices[0].message.tool_calls:
                        tool_calls.append({
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        })
                
                if attempt > 0:
                    info(f"重试成功 (第 {attempt + 1} 次尝试)")
                
                return content, tool_calls
                
            except Exception as e:
                last_error = e
                
                if self._should_retry(e) and attempt < self.MAX_RETRIES:
                    delay = self._calculate_delay(attempt)
                    warn(f"API 调用失败，{delay:.1f}秒后重试 ({attempt + 1}/{self.MAX_RETRIES}): {e}")
                    time.sleep(delay)
                else:
                    break
        
        error_msg = f"调用失败 (重试 {self.MAX_RETRIES} 次后): {last_error}"
        error(error_msg)
        return error_msg, []
    
    def _clean_model_output(self, content: str) -> str:
        """清理模型输出"""
        if not content:
            return content
        
        patterns = [
            r'<\|tool_calls_section_begin\|>',
            r'<\|tool_calls_section_end\|>',
            r'<\|tool_call_begin\|>',
            r'<\|tool_call_end\|>',
            r'<\|tool_call_argument_begin\|>',
            r'<\|tool_call_argument_end\|>',
            r'<\|tool_call_argument\|>',
            r'<\|.*?\|>',
        ]
        
        cleaned = content
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned)
        
        cleaned = re.sub(r'functions\.\w+:\d+\s*', '', cleaned)
        cleaned = re.sub(r'\{\s*"[^"]+"\s*:\s*"[^"]*"[^}]*\}\s*', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def _parse_tool_calls_from_text(self, content: str) -> List[Dict]:
        """从文本中解析工具调用"""
        tool_calls = []
        
        # 模式1: functions.name:args
        pattern1 = r'functions\.([\w_]+):(\d+)\s*\n?\s*(\{.*?\})'
        matches1 = re.findall(pattern1, content, re.DOTALL)
        
        for match in matches1:
            func_name, idx, args_str = match
            try:
                args = json.loads(args_str)
                tool_calls.append({
                    "id": f"tc_{idx}",
                    "type": "function",
                    "function": {
                        "name": func_name,
                        "arguments": json.dumps(args)
                    }
                })
            except json.JSONDecodeError:
                continue
        
        # 模式2: JSON 代码块
        pattern2 = r'```json\s*(.*?)\s*```'
        matches2 = re.findall(pattern2, content, re.DOTALL)
        
        for match in matches2:
            try:
                data = json.loads(match)
                if isinstance(data, dict) and "name" in data and "arguments" in data:
                    tool_calls.append({
                        "id": f"tc_{len(tool_calls)}",
                        "type": "function",
                        "function": {
                            "name": data["name"],
                            "arguments": json.dumps(data["arguments"])
                        }
                    })
            except json.JSONDecodeError:
                continue
        
        return tool_calls
    
    async def call_async(
        self,
        prompt: str,
        system_prompt: str = None,
        tools: List[Dict] = None,
        stream: bool = True
    ) -> Tuple[str, List[Dict]]:
        """异步调用模型（带重试机制）"""
        if not self.client:
            return "客户端未初始化", []
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        last_error = None
        
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                kwargs = {
                    "model": self.config.get("model"),
                    "messages": messages,
                    "stream": stream
                }
                if tools:
                    kwargs["tools"] = tools
                
                api(f"异步调用模型: {self.config.get('model')} (尝试 {attempt + 1})")
                
                response = self.client.chat.completions.create(**kwargs)
                
                if stream:
                    full_content = ""
                    tool_calls = []
                    
                    for chunk in response:
                        if not chunk.choices:
                            continue
                        
                        delta = chunk.choices[0].delta
                        
                        if delta.content:
                            raw_content = delta.content
                            clean_content = self._clean_model_output(raw_content)
                            if clean_content:
                                print(clean_content, end="", flush=True)
                            full_content += raw_content
                        
                        if delta.tool_calls:
                            for tc in delta.tool_calls:
                                while len(tool_calls) <= tc.index:
                                    tool_calls.append({
                                        "id": f"tc_{tc.index}",
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""}
                                    })
                                target = tool_calls[tc.index]
                                if tc.id:
                                    target["id"] = tc.id
                                if tc.function.name:
                                    target["function"]["name"] += tc.function.name
                                if tc.function.arguments:
                                    target["function"]["arguments"] += tc.function.arguments
                    
                    print()
                    
                    full_content = self._clean_model_output(full_content)
                    
                    if not tool_calls and tools:
                        tool_calls = self._parse_tool_calls_from_text(full_content)
                    
                    if attempt > 0:
                        info(f"重试成功 (第 {attempt + 1} 次尝试)")
                    
                    return full_content, tool_calls
                else:
                    content = response.choices[0].message.content or ""
                    content = self._clean_model_output(content)
                    tool_calls = []
                    
                    if response.choices[0].message.tool_calls:
                        for tc in response.choices[0].message.tool_calls:
                            tool_calls.append({
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            })
                    
                    if not tool_calls and tools:
                        tool_calls = self._parse_tool_calls_from_text(content)
                    
                    return content, tool_calls
                    
            except Exception as e:
                last_error = e
                
                if self._should_retry(e) and attempt < self.MAX_RETRIES:
                    delay = self._calculate_delay(attempt)
                    warn(f"API 调用失败，{delay:.1f}秒后重试 ({attempt + 1}/{self.MAX_RETRIES}): {e}")
                    await asyncio.sleep(delay)
                else:
                    break
        
        error_msg = f"调用失败 (重试 {self.MAX_RETRIES} 次后): {last_error}"
        error(error_msg)
        return error_msg, []
    
    async def call_with_messages(
        self,
        messages: List[Dict],
        tools: List[Dict] = None,
        stream: bool = True
    ) -> Tuple[str, List[Dict]]:
        """
        使用完整消息历史调用模型（用于工具调用循环）
        
        Args:
            messages: 完整的消息历史
            tools: 工具定义
            stream: 是否流式输出
            
        Returns:
            (响应文本, 工具调用列表)
        """
        if not self.client:
            return "客户端未初始化", []
        
        try:
            kwargs = {
                "model": self.config.get("model"),
                "messages": messages,
                "stream": stream
            }
            if tools:
                kwargs["tools"] = tools
            
            response = self.client.chat.completions.create(**kwargs)
            
            if stream:
                full_content = ""
                tool_calls = []
                
                for chunk in response:
                    if not chunk.choices:
                        continue
                    
                    delta = chunk.choices[0].delta
                    
                    if delta.content:
                        raw_content = delta.content
                        clean_content = self._clean_model_output(raw_content)
                        if clean_content:
                            print(clean_content, end="", flush=True)
                        full_content += raw_content
                    
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            while len(tool_calls) <= tc.index:
                                tool_calls.append({
                                    "id": f"tc_{tc.index}",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                })
                            target = tool_calls[tc.index]
                            if tc.id:
                                target["id"] = tc.id
                            if tc.function.name:
                                target["function"]["name"] += tc.function.name
                            if tc.function.arguments:
                                target["function"]["arguments"] += tc.function.arguments
                
                if full_content:
                    print()
                
                full_content = self._clean_model_output(full_content)
                
                return full_content, tool_calls
            else:
                content = response.choices[0].message.content or ""
                content = self._clean_model_output(content)
                tool_calls = []
                
                if response.choices[0].message.tool_calls:
                    for tc in response.choices[0].message.tool_calls:
                        tool_calls.append({
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        })
                
                return content, tool_calls
                
        except Exception as e:
            return f"调用失败: {e}", []
    
    async def call_with_messages(
        self,
        messages: List[Dict],
        tools: List[Dict] = None,
        stream: bool = True
    ) -> Tuple[str, List[Dict]]:
        """
        使用完整消息历史调用模型（带重试机制，用于工具调用循环）
        
        Args:
            messages: 完整的消息历史
            tools: 工具定义
            stream: 是否流式输出
            
        Returns:
            (响应文本, 工具调用列表)
        """
        if not self.client:
            return "客户端未初始化", []
        
        last_error = None
        
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                kwargs = {
                    "model": self.config.get("model"),
                    "messages": messages,
                    "stream": stream
                }
                if tools:
                    kwargs["tools"] = tools
                
                api(f"调用模型 (消息历史: {len(messages)}条) (尝试 {attempt + 1})")
                
                response = self.client.chat.completions.create(**kwargs)
                
                if stream:
                    full_content = ""
                    tool_calls = []
                    
                    for chunk in response:
                        if not chunk.choices:
                            continue
                        
                        delta = chunk.choices[0].delta
                        
                        if delta.content:
                            raw_content = delta.content
                            clean_content = self._clean_model_output(raw_content)
                            if clean_content:
                                print(clean_content, end="", flush=True)
                            full_content += raw_content
                        
                        if delta.tool_calls:
                            for tc in delta.tool_calls:
                                while len(tool_calls) <= tc.index:
                                    tool_calls.append({
                                        "id": f"tc_{tc.index}",
                                        "type": "function",
                                        "function": {"name": "", "arguments": ""}
                                    })
                                target = tool_calls[tc.index]
                                if tc.id:
                                    target["id"] = tc.id
                                if tc.function.name:
                                    target["function"]["name"] += tc.function.name
                                if tc.function.arguments:
                                    target["function"]["arguments"] += tc.function.arguments
                    
                    if full_content:
                        print()
                    
                    full_content = self._clean_model_output(full_content)
                    
                    if attempt > 0:
                        info(f"重试成功 (第 {attempt + 1} 次尝试)")
                    
                    return full_content, tool_calls
                else:
                    content = response.choices[0].message.content or ""
                    content = self._clean_model_output(content)
                    tool_calls = []
                    
                    if response.choices[0].message.tool_calls:
                        for tc in response.choices[0].message.tool_calls:
                            tool_calls.append({
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            })
                    
                    return content, tool_calls
                    
            except Exception as e:
                last_error = e
                
                if self._should_retry(e) and attempt < self.MAX_RETRIES:
                    delay = self._calculate_delay(attempt)
                    warn(f"API 调用失败，{delay:.1f}秒后重试 ({attempt + 1}/{self.MAX_RETRIES}): {e}")
                    await asyncio.sleep(delay)
                else:
                    break
        
        error_msg = f"调用失败 (重试 {self.MAX_RETRIES} 次后): {last_error}"
        error(error_msg)
        return error_msg, []


class LeaderAI:
    """Leader AI - 任务规划和协调"""
    
    def __init__(self, ai_dir: str):
        self.ai_dir = ai_dir
        self.root_dir = os.path.dirname(ai_dir)
        
        # 加载配置
        self.config = self._load_config("leader")
        self.worker_config = self._load_config("worker")
        
        # 初始化模块
        self.model = ModelInterface(self.config) if self.config else None
        self.worker_model = ModelInterface(self.worker_config) if self.worker_config else None
        self.task_manager = TaskManager(ai_dir)
        self.mcp_manager = MCPToolManager()
        
        # MCP 工具权限管理
        self._mcp_permissions = {
            "allowed_plugins": set(),      # 永久允许的插件
            "session_allowed": set(),      # 本次任务允许的插件
            "denied_tools": set(),         # 本次拒绝的工具
        }
        
        # 读取指南
        self.leader_guide = self._load_guide("README_for_leader.md")
        self.worker_guide = self._load_guide("README_for_worker.md")
        
        # 加载对话历史（修复：添加持久化上下文记忆）
        self.history_file = os.path.join(ai_dir, "leader_history.json")
        self.messages = self._load_history()
        
        # 任务恢复：检查是否有未完成的任务
        self._check_pending_tasks()
    
    def _check_mcp_permission(self, tool_name: str) -> int:
        """
        检查 MCP 工具调用权限
        
        Returns:
            0: 拒绝
            1: 允许本次
            2: 允许该插件所有命令
            3: 本次任务永久允许
        """
        # 解析插件名
        if "__" not in tool_name:
            return 1  # 非 MCP 工具，直接允许
        
        plugin_name = tool_name.split("__")[0]
        
        # 检查是否已在拒绝列表
        if tool_name in self._mcp_permissions["denied_tools"]:
            return 0
        
        # 检查是否永久允许该插件
        if plugin_name in self._mcp_permissions["allowed_plugins"]:
            return 2
        
        # 检查是否本次任务允许
        if plugin_name in self._mcp_permissions["session_allowed"]:
            return 3
        
        # 需要用户确认
        return -1
    
    def _request_mcp_permission(self, tool_name: str, args: dict) -> int:
        """
        请求用户确认 MCP 工具调用
        
        Returns:
            0: 拒绝
            1: 允许本次
            2: 允许该插件所有命令
            3: 本次任务永久允许
        """
        plugin_name = tool_name.split("__")[0] if "__" in tool_name else "unknown"
        tool_action = tool_name.split("__")[1] if "__" in tool_name else tool_name
        
        # 格式化参数显示
        args_str = ""
        if args:
            for key, value in list(args.items())[:5]:  # 只显示前5个参数
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:100] + "..."
                args_str += f"    {key}: {value_str}\n"
            if len(args) > 5:
                args_str += f"    ... (共 {len(args)} 个参数)\n"
        
        print()
        UI.section("🔒 MCP 工具调用确认")
        print(f"  插件: {UI.CYAN}{plugin_name}{UI.END}")
        print(f"  工具: {UI.GREEN}{tool_action}{UI.END}")
        if args_str:
            print(f"  参数:")
            print(args_str.rstrip())
        print()
        print(f"  {UI.BOLD}请选择操作:{UI.END}")
        print(f"    {UI.RED}1. 拒绝{UI.END} - 不执行此操作")
        print(f"    {UI.YELLOW}2. 本次允许{UI.END} - 仅允许本次调用")
        print(f"    {UI.GREEN}3. 允许该插件所有命令{UI.END} - 本次任务中信任此插件")
        print(f"    {UI.CYAN}4. 允许所有插件{UI.END} - 本次任务不再询问")
        print()
        
        while True:
            try:
                choice = input(f"  请选择 [1-4]: ").strip()
                if choice == "1":
                    return 0
                elif choice == "2":
                    return 1
                elif choice == "3":
                    plugin_name = tool_name.split("__")[0] if "__" in tool_name else ""
                    if plugin_name:
                        self._mcp_permissions["allowed_plugins"].add(plugin_name)
                    return 2
                elif choice == "4":
                    self._mcp_permissions["session_allowed"].add("__all__")
                    return 3
                else:
                    UI.warn("请输入 1-4")
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
    
    def _check_pending_tasks(self):
        """检查未完成的任务（任务恢复功能）"""
        in_progress = self.task_manager.get_in_progress_tasks()
        pending = self.task_manager.get_pending_tasks()
        
        if in_progress or pending:
            debug(f"发现 {len(in_progress)} 个进行中任务, {len(pending)} 个待处理任务")
    
    def _load_config(self, role: str) -> Optional[Dict]:
        """加载模型配置"""
        config_file = os.path.join(self.ai_dir, f"{role}_model.config")
        if not os.path.exists(config_file):
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    
    def _load_guide(self, filename: str) -> str:
        """加载指南文档"""
        template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", filename)
        if os.path.exists(template_path):
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except:
                pass
        return ""
    def is_ready(self) -> bool:
        """检查是否准备就绪"""
        return self.model is not None and self.worker_model is not None
    
    def _load_history(self) -> List[Dict]:
        """加载对话历史（修复P0：添加历史加载）"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # 初始化为包含系统提示的列表
        return [{"role": "system", "content": self._build_system_prompt()}]
    
    def _save_history(self):
        """保存对话历史（修复P0：添加历史保存）"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            UI.warn(f"保存对话历史失败: {e}")
    
    def _build_system_prompt(self) -> str:
        """构建系统提示"""
        # 获取任务列表
        tasks = self.task_manager.get_all_tasks()
        tasks_summary = ""
        if tasks:
            tasks_summary = "\n当前任务列表:\n"
            for t in tasks[:10]:  # 只显示前10个
                status_icon = {"pending": "○", "in_progress": "◐", "completed": "●", "failed": "✗"}.get(t.get("status"), "○")
                deps = t.get("dependencies", [])
                deps_str = f" [依赖: {', '.join(deps)}]" if deps else ""
                tasks_summary += f"  {status_icon} {t.get('id')}: {t.get('title')}{deps_str}\n"
        
        return f"""你是 Leader AI，负责任务规划和协调。

{self.leader_guide}

当前项目目录: {self.root_dir}

## 🚨 核心工作流程（必须严格遵守）

1. **接收需求** → 分析用户需求
2. **创建任务** → 使用 `create_task` 工具创建任务
3. **分配任务** → 使用 `assign_task` 工具分配给 Worker AI
4. **等待完成** → Worker 执行完毕后检查结果
5. **继续或汇报** → 分配下一个任务或向用户汇报

## ⚠️ 重要规则

- **禁止直接使用 MCP 工具执行代码编写任务**（如 write_file）
- 所有执行类任务必须通过 `assign_task` 分配给 Worker AI
- 你只负责：规划、创建任务、分配任务、监控进度、汇报结果

## 🔗 任务依赖机制

创建任务时可以指定 `dependencies` 参数，表示该任务依赖的其他任务：
- 只有当所有依赖任务完成后，当前任务才会被执行
- 使用 `assign_tasks_parallel` 时，系统会自动检测依赖并按顺序执行
- 系统还会自动检测文件冲突，避免多个 Worker 同时修改同一文件

**示例**：
```json
{{
  "title": "测试用户模块",
  "description": "编写用户模块的单元测试",
  "dependencies": ["task_001"],  // 等待 task_001 完成
  "files_to_modify": ["tests/test_user.py"]
}}
```

当前任务状态:
{json.dumps(self.task_manager.get_statistics(), ensure_ascii=False, indent=2)}
{tasks_summary}
"""
    
    def _summarize_old_messages(self, messages: List[Dict], keep_recent: int = 10) -> List[Dict]:
        """
        智能摘要旧消息（上下文窗口管理）
        
        保留策略：
        - 保留系统消息
        - 保留最近 N 条消息
        - 将中间消息替换为摘要
        
        Args:
            messages: 消息列表
            keep_recent: 保留最近多少条消息
            
        Returns:
            压缩后的消息列表
        """
        if len(messages) <= keep_recent + 2:
            return messages
        
        # 分离系统消息
        system_msg = None
        other_messages = []
        for m in messages:
            if m.get("role") == "system":
                system_msg = m
            else:
                other_messages.append(m)
        
        # 保留最近的消息
        recent_messages = other_messages[-keep_recent:]
        old_messages = other_messages[:-keep_recent]
        
        if not old_messages:
            return messages
        
        # 生成摘要
        summary_parts = []
        for m in old_messages:
            role = m.get("role", "unknown")
            content = m.get("content", "")
            
            if role == "user":
                summary_parts.append(f"用户: {content[:100]}...")
            elif role == "assistant":
                # 检查是否有工具调用
                if m.get("tool_calls"):
                    tool_names = [tc.get("function", {}).get("name", "") for tc in m["tool_calls"]]
                    summary_parts.append(f"助手调用了工具: {', '.join(tool_names[:3])}")
                elif content:
                    summary_parts.append(f"助手: {content[:100]}...")
            elif role == "tool":
                summary_parts.append(f"工具结果: {str(content)[:50]}...")
        
        # 创建摘要消息
        summary_text = "【历史摘要】\n" + "\n".join(summary_parts[-20:])  # 最多20条摘要
        
        summary_msg = {
            "role": "user",
            "content": f"[系统自动生成的历史摘要]\n{summary_text}\n\n请继续基于以上历史上下文工作。"
        }
        
        # 组合结果
        result = []
        if system_msg:
            result.append(system_msg)
        result.append(summary_msg)
        result.extend(recent_messages)
        
        debug(f"上下文压缩: {len(messages)} -> {len(result)} 条消息")
        
        return result
    
    def _manage_context(self, max_messages: int = 50) -> bool:
        """
        管理上下文窗口，防止溢出
        
        Args:
            max_messages: 最大消息数量
            
        Returns:
            是否进行了压缩
        """
        if len(self.messages) <= max_messages:
            return False
        
        warn(f"上下文消息过多 ({len(self.messages)} 条)，正在进行智能压缩...")
        
        # 进行智能压缩
        self.messages = self._summarize_old_messages(self.messages, keep_recent=15)
        
        # 保存压缩后的历史
        self._save_history()
        
        return True
    
    async def start_session(self):
        """启动 Leader 会话"""
        if not self.is_ready():
            UI.error("Leader AI 未正确配置")
            return
        
        # 静默初始化 MCP 工具（隐藏服务器启动信息）
        with suppress_stdout():
            await self.mcp_manager.initialize(silent=True)
        
        # 显示 MCP 启动提示
        MCPServerSuppressor.show_startup_message(list(self.mcp_manager.server_params.keys()))
        
        UI.section("Leader AI 会话")
        print(f"  项目目录: {self.root_dir}")
        print(f"  Leader 模型: {self.config.get('model')}")
        print(f"  Worker 模型: {self.worker_config.get('model')}")
        print()
        print("  多行输入支持:")
        print("    - 以 \\ 结尾继续输入下一行")
        print("    - 输入 ``` 开始多行块，再输入 ``` 结束")
        print("    - 或输入 \"\"\" 开始多行块，再输入 \"\"\" 结束")
        print()
        print("  命令:")
        print("    - exit: 退出")
        print("    - status: 查看进度")
        print("    - clear: 清空已完成的任务")
        print()
        
        input_handler = InputHandler("", allow_multiline=True)
        
        while True:
            try:
                print(f"{UI.CYAN}Leader>{UI.END} ", end="", flush=True)
                user_input = input_handler.get_input()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ["exit", "quit"]:
                    break
                
                if user_input.lower() == "status":
                    self.task_manager.show_progress()
                    continue
                
                if user_input.lower() == "clear":
                    self.task_manager.clear_completed_tasks()
                    # 同时清空对话历史
                    system_prompt = self._build_system_prompt()
                    self.messages = [{"role": "system", "content": system_prompt}]
                    self._save_history()
                    UI.success("已清空任务和对话历史")
                    continue
                
                # 处理用户输入
                await self.process_user_input(user_input)
                
            except KeyboardInterrupt:
                print("\n")
                break
    
    async def process_user_input(self, user_input: str):
        """处理用户输入（修复P0：使用持久化的上下文记忆）"""
        # 获取 MCP 工具定义
        tools = await self.mcp_manager.get_tools()
        
        # 添加进化工具
        tools.extend(self._get_evolution_tools())
        
        # 更新系统提示（任务状态可能已变化）
        updated_system_prompt = self._build_system_prompt()
        
        # 更新self.messages的第一条系统消息
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = updated_system_prompt
        else:
            self.messages.insert(0, {"role": "system", "content": updated_system_prompt})
        
        # 添加用户消息
        self.messages.append({"role": "user", "content": user_input})
        
        # 调用模型（使用call_with_messages以使用完整历史）
        print(f"\n{UI.BLUE}[Leader]{UI.END} ", end="", flush=True)
        response, tool_calls = await self.model.call_with_messages(self.messages, tools, stream=True)
        
        # 如果有响应内容，添加到历史
        if response:
            self.messages.append({"role": "assistant", "content": response})
        
        # 处理工具调用循环
        if tool_calls:
            await self._handle_tool_calls_loop(tool_calls, tools)
        
        # 保存历史
        self._save_history()
        
        # 显示任务状态
        self.task_manager.show_progress()
    
    async def _handle_tool_calls_loop(self, tool_calls: List[Dict], tools: List[Dict]):
        """
        处理工具调用循环（修复P0：直接使用self.messages）
        
        Args:
            tool_calls: 工具调用列表
            tools: 工具定义
        """
        max_iterations = 20
        iteration = 0
        
        while tool_calls and iteration < max_iterations:
            iteration += 1
            
            # 添加助手响应（工具调用）
            self.messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": tool_calls
            })
            
            # 处理所有工具调用
            for tc in tool_calls:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except:
                    args = {}
                
                UI.info(f"调用: {name}")
                
                # ===== 任务管理工具 =====
                if name == "create_task":
                    task = self.task_manager.create_task(
                        title=args.get("title", "未命名任务"),
                        description=args.get("description", ""),
                        task_type=args.get("type", "code"),
                        priority=args.get("priority", 3),
                        dependencies=args.get("dependencies", []),
                        files_to_modify=args.get("files_to_modify", []),
                        acceptance_criteria=args.get("acceptance_criteria", [])
                    )
                    
                    # 构建结果消息
                    result = f"任务已创建: {task['id']}\n标题: {task['title']}"
                    if task.get("dependencies"):
                        result += f"\n依赖: {', '.join(task['dependencies'])}"
                    result += "\n请使用 assign_task 工具将此任务分配给 Worker AI 执行。"
                    UI.success(f"任务已创建: {task['id']}")
                
                elif name == "assign_task":
                    task_id = args.get("task_id")
                    instructions = args.get("instructions", "")
                    
                    task = self.task_manager.get_task(task_id)
                    if not task:
                        result = f"错误: 未找到任务 {task_id}"
                    elif task.get("status") != "pending":
                        result = f"错误: 任务 {task_id} 状态为 {task.get('status')}，不是待处理状态"
                    else:
                        # 检查依赖是否满足
                        dependencies = task.get("dependencies", [])
                        unmet_deps = self._check_unmet_dependencies(dependencies)
                        
                        if unmet_deps:
                            result = f"错误: 任务 {task_id} 的依赖未满足\n未完成的依赖: {', '.join(unmet_deps)}\n请先完成依赖任务。"
                        else:
                            # 分配任务给 Worker 执行
                            result = await self._assign_task_to_worker(task, instructions)
                
                elif name == "assign_tasks_parallel":
                    # 并行分配多个任务（带智能调度）
                    task_ids = args.get("task_ids", [])
                    max_concurrent = args.get("max_concurrent", 3)
                    
                    if not task_ids:
                        result = "错误: 未提供任务ID列表"
                    else:
                        result = await self._assign_tasks_parallel_smart(task_ids, max_concurrent)
                
                elif name == "list_tasks":
                    status_filter = args.get("status", "all")
                    tasks = self.task_manager.get_all_tasks()
                    
                    if status_filter != "all":
                        tasks = [t for t in tasks if t.get("status") == status_filter]
                    
                    if not tasks:
                        result = f"没有{status_filter if status_filter != 'all' else ''}任务"
                    else:
                        lines = [f"任务列表 ({len(tasks)}个):\n"]
                        for t in tasks:
                            status_icon = {"pending": "○", "in_progress": "◐", "completed": "●", "failed": "✗"}.get(t.get("status"), "○")
                            deps = t.get("dependencies", [])
                            deps_str = f" [依赖: {', '.join(deps)}]" if deps else ""
                            files = t.get("files_to_modify", [])
                            files_str = f" [文件: {len(files)}个]" if files else ""
                            lines.append(f"  {status_icon} {t['id']}: {t['title']} [{t.get('status', 'unknown')}]{deps_str}{files_str}")
                        result = "\n".join(lines)
                
                elif name == "get_task_result":
                    task_id = args.get("task_id")
                    task = self.task_manager.get_task(task_id)
                    if not task:
                        result = f"错误: 未找到任务 {task_id}"
                    else:
                        result = f"任务: {task['title']}\n状态: {task.get('status')}\n"
                        if task.get("result_summary"):
                            result += f"结果: {task['result_summary']}\n"
                        if task.get("error_log"):
                            result += f"错误: {task['error_log']}\n"
                
                # ===== 插件管理工具 =====
                elif name == "search_plugin":
                    results = PluginManager.search(args.get("query", ""))
                    result = self._format_search_results(results)
                elif name == "install_plugin":
                    success = await PluginManager.install(args.get("name", ""))
                    if success:
                        await self.mcp_manager.initialize()
                        tools = await self.mcp_manager.get_tools()
                        tools.extend(self._get_evolution_tools())
                    result = "安装成功" if success else "安装失败"
                elif name == "analyze_gap":
                    result = "分析完成"
                
                # ===== MCP 工具 =====
                elif "__" in name:
                    result = await self.mcp_manager.call(name, args)
                else:
                    result = f"未知工具: {name}"
                
                # 添加工具结果
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": name,
                    "content": result
                })
            
            # 继续对话
            print(f"{UI.CYAN}[继续]{UI.END} ", end="", flush=True)
            response, tool_calls = await self.model.call_with_messages(self.messages, tools, stream=True)
            
            if response:
                self.messages.append({"role": "assistant", "content": response})
    
    def _get_evolution_tools(self) -> List[Dict]:
        """获取进化工具定义"""
        return [
            # ===== 任务管理工具（Leader 专用）=====
            {
                "type": "function",
                "function": {
                    "name": "create_task",
                    "description": "创建一个新任务。Leader 必须先用此工具创建任务，再分配给 Worker。支持设置任务依赖，只有依赖任务完成后才会执行当前任务。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "任务标题（简洁）"},
                            "description": {"type": "string", "description": "任务详细描述"},
                            "type": {"type": "string", "enum": ["code", "doc", "config", "test", "review", "refactor", "fix"], "description": "任务类型"},
                            "priority": {"type": "integer", "minimum": 1, "maximum": 5, "description": "优先级（1最高，5最低）"},
                            "dependencies": {"type": "array", "items": {"type": "string"}, "description": "依赖的任务ID列表，这些任务必须完成后当前任务才能执行"},
                            "files_to_modify": {"type": "array", "items": {"type": "string"}, "description": "需要修改的文件路径列表（用于检测并发冲突）"},
                            "acceptance_criteria": {"type": "array", "items": {"type": "string"}, "description": "验收标准"}
                        },
                        "required": ["title", "description"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "assign_task",
                    "description": "将任务分配给 Worker AI 执行。Leader 必须在创建任务后调用此工具。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "要分配的任务ID"},
                            "instructions": {"type": "string", "description": "给 Worker 的额外执行指令"}
                        },
                        "required": ["task_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "assign_tasks_parallel",
                    "description": "并行分配多个独立任务给 Worker AI 执行。用于无依赖关系的任务并发执行。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_ids": {"type": "array", "items": {"type": "string"}, "description": "要并行执行的任务ID列表"},
                            "max_concurrent": {"type": "integer", "minimum": 1, "maximum": 5, "description": "最大并发数（默认3）"}
                        },
                        "required": ["task_ids"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_tasks",
                    "description": "列出所有任务及其状态",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "status": {"type": "string", "enum": ["all", "pending", "in_progress", "completed", "failed"], "description": "筛选状态"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_task_result",
                    "description": "获取已完成任务的详细结果",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string", "description": "任务ID"}
                        },
                        "required": ["task_id"]
                    }
                }
            },
            # ===== 插件管理工具 =====
            {
                "type": "function",
                "function": {
                    "name": "search_plugin",
                    "description": "搜索MCP插件",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "install_plugin",
                    "description": "安装MCP插件",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "插件名称"}
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_gap",
                    "description": "分析能力差距",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task": {"type": "string", "description": "任务描述"}
                        }
                    }
                }
            }
        ]
    
    def _check_unmet_dependencies(self, dependencies: List[str]) -> List[str]:
        """
        检查未满足的依赖
        
        Args:
            dependencies: 依赖任务ID列表
            
        Returns:
            未完成的依赖任务ID列表
        """
        unmet = []
        for dep_id in dependencies:
            dep_task = self.task_manager.get_task(dep_id)
            if not dep_task or dep_task.get("status") != "completed":
                unmet.append(dep_id)
        return unmet
    
    def _detect_file_conflicts(self, tasks: List[Dict]) -> Dict[str, List[str]]:
        """
        检测任务间的文件冲突
        
        Args:
            tasks: 任务列表
            
        Returns:
            冲突映射: {文件路径: [冲突的任务ID列表]}
        """
        file_to_tasks = {}
        
        for task in tasks:
            files = task.get("files_to_modify", [])
            for f in files:
                if f not in file_to_tasks:
                    file_to_tasks[f] = []
                file_to_tasks[f].append(task["id"])
        
        # 只保留有冲突的文件
        conflicts = {f: task_ids for f, task_ids in file_to_tasks.items() if len(task_ids) > 1}
        return conflicts
    
    def _get_execution_groups(self, tasks: List[Dict]) -> List[List[Dict]]:
        """
        根据依赖关系将任务分组，每组内的任务可以并行执行
        
        Args:
            tasks: 任务列表
            
        Returns:
            执行分组列表，每组内的任务互不依赖
        """
        if not tasks:
            return []
        
        # 构建任务ID到任务的映射
        task_map = {t["id"]: t for t in tasks}
        task_ids = set(task_map.keys())
        
        # 构建依赖图
        dependencies = {}
        for t in tasks:
            deps = set(t.get("dependencies", []))
            # 只考虑列表内的依赖
            dependencies[t["id"]] = deps & task_ids
        
        # 检测文件冲突，将冲突的任务视为互相依赖
        conflicts = self._detect_file_conflicts(tasks)
        for file_path, conflicting_ids in conflicts.items():
            for i, tid1 in enumerate(conflicting_ids):
                for tid2 in conflicting_ids[i+1:]:
                    # 添加双向依赖（视为冲突）
                    dependencies[tid1].add(tid2)
                    dependencies[tid2].add(tid1)
        
        # 拓扑排序分组
        groups = []
        remaining = set(task_ids)
        completed = set()
        
        while remaining:
            # 找出所有依赖已满足的任务
            ready = []
            for tid in remaining:
                if dependencies[tid] <= completed:
                    ready.append(task_map[tid])
            
            if not ready:
                # 存在循环依赖，强制选一个（不应该发生，但作为保险）
                warn(f"检测到循环依赖，强制选择任务: {remaining}")
                ready = [task_map[next(iter(remaining))]]
            
            groups.append(ready)
            for t in ready:
                completed.add(t["id"])
                remaining.discard(t["id"])
        
        return groups
    
    def _format_search_results(self, results: list) -> str:
        """格式化搜索结果"""
        if not results:
            return "未找到匹配插件"
        
        lines = ["找到以下插件：\n"]
        for p in results[:10]:
            lines.append(f"- {p.name}: {p.description}")
            if hasattr(p, 'required_env') and p.required_env:
                lines.append(f"  需要环境变量: {', '.join(p.required_env)}")
        
        return "\n".join(lines)
    
    async def plan_tasks(self, user_request: str) -> bool:
        """规划任务"""
        if not self.model:
            UI.error("模型未初始化")
            return False
        
        UI.info("正在分析需求并规划任务...")
        
        system_prompt = f"""你是任务规划专家。

{self.leader_guide}

请根据用户需求，创建详细的任务列表。
"""
        
        response, _ = self.model.call(user_request, system_prompt)
        tasks = self._parse_tasks_from_response(response)
        
        for task_data in tasks:
            self.task_manager.create_task(**task_data)
        
        UI.success(f"已创建 {len(tasks)} 个任务")
        self.task_manager.show_progress()
        
        return True
    
    def _parse_tasks_from_response(self, response: str) -> List[Dict]:
        """从模型响应中解析任务"""
        tasks = []
        
        try:
            json_blocks = re.findall(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            
            for block in json_blocks:
                try:
                    data = json.loads(block)
                    if isinstance(data, list):
                        tasks.extend(data)
                    elif isinstance(data, dict) and "tasks" in data:
                        tasks.extend(data["tasks"])
                except:
                    continue
            
            if not tasks:
                data = json.loads(response)
                if isinstance(data, list):
                    tasks = data
                elif isinstance(data, dict) and "tasks" in data:
                    tasks = data["tasks"]
                    
        except json.JSONDecodeError:
            tasks = [{
                "title": "执行用户需求",
                "description": response,
                "type": "code",
                "priority": 3,
                "dependencies": [],
            }]
        
        return tasks
    
    async def _assign_task_to_worker(self, task: Dict, instructions: str = "") -> str:
        """
        分配任务给 Worker（内部方法，返回字符串结果）
        
        Args:
            task: 任务字典
            instructions: 额外指令
            
        Returns:
            执行结果字符串
        """
        if not self.worker_model:
            return "错误: Worker 模型未配置"
        
        # 设置任务状态为进行中
        self.task_manager.set_task_status(task["id"], "in_progress")
        
        # 如果有额外指令，添加到任务描述中
        if instructions:
            task = task.copy()
            task["description"] = f"{task.get('description', '')}\n\n额外指令: {instructions}"
        
        # 创建 Worker 实例并执行
        worker = WorkerAI(
            ai_dir=self.ai_dir,
            task=task,
            model_interface=self.worker_model,
            mcp_manager=self.mcp_manager,
            leader=self
        )
        
        UI.section(f"Worker 执行任务: {task['title']}")
        success, result = await worker.execute()
        
        if success:
            self.task_manager.set_task_status(task["id"], "completed", result=result)
            return f"✅ 任务 {task['id']} 完成\n结果: {result[:500]}..." if len(result) > 500 else f"✅ 任务 {task['id']} 完成\n结果: {result}"
        else:
            self.task_manager.set_task_status(task["id"], "failed", error=result)
            return f"❌ 任务 {task['id']} 失败\n错误: {result[:500]}..." if len(result) > 500 else f"❌ 任务 {task['id']} 失败\n错误: {result}"
    
    async def _assign_tasks_parallel(self, task_ids: List[str], max_concurrent: int = 3) -> str:
        """
        并行分配多个任务给 Worker 执行（已弃用，请使用 _assign_tasks_parallel_smart）
        """
        return await self._assign_tasks_parallel_smart(task_ids, max_concurrent)
    
    async def _assign_tasks_parallel_smart(self, task_ids: List[str], max_concurrent: int = 3) -> str:
        """
        智能并行分配多个任务给 Worker 执行
        
        特性：
        1. 自动检测任务依赖，按依赖顺序执行
        2. 检测文件冲突，避免多个 Worker 同时修改同一文件
        3. 自动分组并行执行无冲突的任务
        
        Args:
            task_ids: 任务ID列表
            max_concurrent: 最大并发数
            
        Returns:
            执行结果汇总
        """
        if not self.worker_model:
            return "错误: Worker 模型未配置"
        
        # 获取所有待处理任务
        tasks = []
        invalid_ids = []
        dependency_blocked = []
        
        all_tasks = self.task_manager.get_all_tasks()
        task_status = {t["id"]: t.get("status") for t in all_tasks}
        
        for task_id in task_ids:
            task = self.task_manager.get_task(task_id)
            if not task:
                invalid_ids.append(task_id)
            elif task.get("status") != "pending":
                invalid_ids.append(f"{task_id}(状态:{task.get('status')})")
            else:
                # 检查依赖是否满足（检查所有依赖，不只是列表内的）
                dependencies = task.get("dependencies", [])
                unmet_deps = [d for d in dependencies if task_status.get(d) != "completed"]
                
                if unmet_deps:
                    dependency_blocked.append(f"{task_id}(依赖:{','.join(unmet_deps)})")
                else:
                    tasks.append(task)
        
        # 构建结果消息
        messages = []
        if invalid_ids:
            messages.append(f"无效任务: {', '.join(invalid_ids)}")
        if dependency_blocked:
            messages.append(f"依赖未满足: {', '.join(dependency_blocked)}")
        
        if not tasks:
            return "错误: 没有可执行的任务\n" + "\n".join(messages)
        
        if messages:
            info("\n".join(messages))
        
        # 检测文件冲突
        conflicts = self._detect_file_conflicts(tasks)
        if conflicts:
            conflict_info = []
            for f, task_ids in conflicts.items():
                conflict_info.append(f"  {f}: {', '.join(task_ids)}")
            info(f"检测到文件冲突:\n" + "\n".join(conflict_info))
        
        # 按依赖和冲突分组
        execution_groups = self._get_execution_groups(tasks)
        
        info(f"开始执行 {len(tasks)} 个任务，分为 {len(execution_groups)} 批（最大并发: {max_concurrent}）")
        
        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}
        
        async def execute_with_semaphore(task: Dict):
            async with semaphore:
                task_log(f"Worker 开始: {task['title']}")
                self.task_manager.set_task_status(task["id"], "in_progress")
                
                worker = WorkerAI(
                    ai_dir=self.ai_dir,
                    task=task,
                    model_interface=self.worker_model,
                    mcp_manager=self.mcp_manager,
                    leader=self
                )
                
                success, result = await worker.execute()
                
                if success:
                    self.task_manager.set_task_status(task["id"], "completed", result=result)
                    results[task["id"]] = f"✅ 完成"
                else:
                    self.task_manager.set_task_status(task["id"], "failed", error=result)
                    results[task["id"]] = f"❌ 失败: {result[:100]}"
        
        # 分批执行
        start_time = time.time()
        
        for group_idx, group in enumerate(execution_groups):
            if len(execution_groups) > 1:
                info(f"执行第 {group_idx + 1}/{len(execution_groups)} 批任务 ({len(group)} 个)")
            
            # 检查这批任务是否有前置失败导致依赖不满足
            ready_tasks = []
            for t in group:
                deps = t.get("dependencies", [])
                failed_deps = [d for d in deps if results.get(d, "").startswith("❌")]
                if failed_deps:
                    results[t["id"]] = f"⏭️ 跳过: 依赖任务失败 ({', '.join(failed_deps)})"
                else:
                    ready_tasks.append(t)
            
            if ready_tasks:
                await asyncio.gather(*[execute_with_semaphore(t) for t in ready_tasks])
        
        elapsed = time.time() - start_time
        
        # 显示进度
        self._show_progress_bar(len(tasks), elapsed)
        
        # 汇总结果
        completed = sum(1 for r in results.values() if "✅" in r)
        failed = sum(1 for r in results.values() if "❌" in r)
        skipped = sum(1 for r in results.values() if "⏭️" in r)
        
        summary = f"\n执行完成 (耗时: {elapsed:.1f}秒)\n"
        summary += f"  成功: {completed}/{len(tasks)}\n"
        summary += f"  失败: {failed}/{len(tasks)}\n"
        if skipped > 0:
            summary += f"  跳过: {skipped}/{len(tasks)}\n"
        if dependency_blocked:
            summary += f"  依赖阻塞: {len(dependency_blocked)}\n"
        
        summary += "\n任务结果:\n"
        for task_id in task_ids:
            if task_id in results:
                summary += f"  - {task_id}: {results[task_id]}\n"
        
        return summary
    
    def _show_progress_bar(self, total: int, elapsed: float):
        """显示进度条"""
        stats = self.task_manager.get_statistics()
        completed = stats.get("completed", 0)
        failed = stats.get("failed", 0)
        total_tasks = stats.get("total", 1)
        
        progress = completed / total_tasks if total_tasks > 0 else 0
        bar_length = 30
        filled = int(bar_length * progress)
        
        bar = f"{'█' * filled}{'░' * (bar_length - filled)}"
        
        print(f"\n{UI.CYAN}[进度]{UI.END} [{UI.GREEN}{bar}{UI.END}] {progress*100:.0f}% | "
              f"完成: {completed} | 失败: {failed} | 耗时: {elapsed:.1f}s")
    
    async def assign_task_to_worker(self, task: Dict) -> Tuple[bool, str]:
        """分配任务给 Worker"""
        if not self.worker_model:
            return False, "Worker 模型未配置"
        
        self.task_manager.set_task_status(task["id"], "in_progress")
        
        worker = WorkerAI(
            ai_dir=self.ai_dir,
            task=task,
            model_interface=self.worker_model,
            mcp_manager=self.mcp_manager,
            leader=self
        )
        
        success, result = await worker.execute()
        
        if success:
            self.task_manager.set_task_status(task["id"], "completed", result=result)
        else:
            self.task_manager.set_task_status(task["id"], "failed", error=result)
        
        return success, result
    
    def request_user_help(self, message: str) -> str:
        """向用户请求帮助"""
        UI.section("需要您的帮助")
        print(f"\n  {message}\n")
        
        response = UI.input("请提供指导或帮助")
        return response


class WorkerAI:
    """Worker AI - 任务执行"""
    
    def __init__(
        self,
        ai_dir: str,
        task: Dict,
        model_interface: ModelInterface,
        mcp_manager: MCPToolManager,
        leader: LeaderAI
    ):
        self.ai_dir = ai_dir
        self.root_dir = os.path.dirname(ai_dir)
        self.task = task
        self.model = model_interface
        self.mcp_manager = mcp_manager
        self.leader = leader
        self.worker_guide = self._load_guide()
        self.tools = None
    
    def _load_guide(self) -> str:
        """加载 Worker 指南"""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "templates",
            "README_for_worker.md"
        )
        if os.path.exists(template_path):
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except:
                pass
        return ""
    
    async def execute(self) -> Tuple[bool, str]:
        """执行任务"""
        try:
            # 确保 MCP 管理器已初始化
            if not self.mcp_manager:
                return False, "MCP 管理器未初始化"
            
            # 重新初始化以确保工具可用
            await self.mcp_manager.initialize()
            
            # 获取 MCP 工具
            self.tools = await self.mcp_manager.get_tools()
            
            if not self.tools:
                UI.warn("未找到可用的 MCP 工具，请先安装插件: ai install <plugin-name>")
            
            # 构建任务提示
            system_prompt = f"""你是 Worker AI，负责执行具体任务。

{self.worker_guide}

当前任务:
- ID: {self.task.get('id')}
- 标题: {self.task.get('title')}
- 描述: {self.task.get('description')}
- 类型: {self.task.get('type')}
- 需要修改的文件: {self.task.get('files_to_modify', [])}
- 验收标准: {self.task.get('acceptance_criteria', [])}

工作目录: {self.root_dir}

规则：
1. 不要向用户请求交互或帮助
2. 使用可用的 MCP 工具完成任务
3. 如果遇到无法解决的问题，说明具体错误
4. 完成后提供简要结果摘要

可用工具数量: {len(self.tools)}
"""
            
            user_prompt = f"请执行任务: {self.task.get('title')}\n\n{self.task.get('description')}"
            
            # 初始化消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            return await self._execution_loop(messages)
            
        except Exception as e:
            import traceback
            return False, f"执行异常: {e}\n{traceback.format_exc()}"
    
    async def _execution_loop(self, messages: List[Dict]) -> Tuple[bool, str]:
        """执行循环（修复P1：添加上下文窗口管理）"""
        max_iterations = 20
        iteration = 0
        max_message_count = 50  # 最大消息数（修复P1：防止上下文溢出）
        
        while iteration < max_iterations:
            iteration += 1
            
            # 修复P1：裁剪消息历史（保留系统提示 + 最近的消息）
            if len(messages) > max_message_count:
                # 保留system消息（第一条）+ 最近的消息
                system_msg = messages[0] if messages[0]["role"] == "system" else None
                recent_messages = messages[-(max_message_count-1):]
                messages = ([system_msg] if system_msg else []) + recent_messages
                UI.warn(f"消息历史已裁剪至 {len(messages)} 条以防止溢出")
            
            # 使用完整的消息历史调用模型
            response, tool_calls = await self.model.call_with_messages(messages, self.tools, stream=True)
            
            # 添加助手响应
            if response or tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": response if response else None,
                    "tool_calls": tool_calls if tool_calls else None
                })
            
            # 如果没有工具调用，任务完成
            if not tool_calls:
                return True, response or "任务完成"
            
            # 处理工具调用
            for tc in tool_calls:
                result = await self._handle_tool_call(tc)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": tc["function"]["name"],
                    "content": result
                })
        
        return False, "超过最大迭代次数"
    
    async def _handle_tool_call(self, tc: Dict) -> str:
        """处理工具调用"""
        name = tc["function"]["name"]
        
        try:
            args = json.loads(tc["function"]["arguments"])
        except:
            args = {}
        
        UI.info(f"执行: {name}")
        
        # MCP 工具调用
        if "__" in name:
            result = await self.mcp_manager.call(name, args)
            return result
        
        # 内置工具
        if name == "report_error_to_leader":
            return self._report_to_leader(args.get("error", ""))
        
        return f"未知工具: {name}"
    
    def _report_to_leader(self, error: str) -> str:
        """向 Leader 报告错误"""
        self.leader.task_manager.add_note(
            self.task["id"],
            f"Worker 报告错误: {error}",
            "worker"
        )
        return f"已将错误报告给 Leader: {error}"


async def run_leader_worker_session(ai_dir: str):
    """启动 Leader-Worker 会话"""
    leader = LeaderAI(ai_dir)
    await leader.start_session()
