"""
AI CLI Leader-Worker 核心（已修复 MCP 工具调用）
实现 Leader AI 和 Worker AI 的协作机制
"""

import os
import sys
import json
import re
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from ..config_mgr import ConfigManager
from ..plugin import PluginManager, MCPToolManager
from ..ui import UI
from .task_manager import TaskManager
from .input_handler import InputHandler


class ModelInterface:
    """模型接口 - 用于调用大模型"""
    
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
        except ImportError:
            UI.error("未安装 openai 库")
        except Exception as e:
            UI.error(f"初始化客户端失败: {e}")
    
    def call(
        self,
        prompt: str,
        system_prompt: str = None,
        tools: List[Dict] = None,
        stream: bool = False
    ) -> Tuple[str, List[Dict]]:
        """调用模型"""
        if not self.client:
            return "客户端未初始化", []
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            kwargs = {
                "model": self.config.get("model"),
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools
            
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
            
            return content, tool_calls
            
        except Exception as e:
            return f"调用失败: {e}", []
    
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
        """异步调用模型"""
        if not self.client:
            return "客户端未初始化", []
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
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
                
                print()
                
                full_content = self._clean_model_output(full_content)
                
                if not tool_calls and tools:
                    tool_calls = self._parse_tool_calls_from_text(full_content)
                
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
            return f"调用失败: {e}", []
    
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
        
        # 读取指南
        self.leader_guide = self._load_guide("README_for_leader.md")
        self.worker_guide = self._load_guide("README_for_worker.md")
    
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
    
    async def start_session(self):
        """启动 Leader 会话"""
        if not self.is_ready():
            UI.error("Leader AI 未正确配置")
            return
        
        # 初始化 MCP 工具
        await self.mcp_manager.initialize()
        
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
                    continue
                
                # 处理用户输入
                await self.process_user_input(user_input)
                
            except KeyboardInterrupt:
                print("\n")
                break
    
    async def process_user_input(self, user_input: str):
        """处理用户输入"""
        # 获取 MCP 工具定义
        tools = await self.mcp_manager.get_tools()
        
        # 添加进化工具
        tools.extend(self._get_evolution_tools())
        
        # 构建系统提示
        system_prompt = f"""你是 Leader AI，负责任务规划和协调。

{self.leader_guide}

当前项目目录: {self.root_dir}

你的职责：
1. 分析用户需求，拆解为可执行的子任务
2. 创建和更新 tasks.json
3. 分配任务给 Worker AI 执行
4. 监控任务进度
5. 当无法完成任务时，向用户请求帮助

当前任务状态:
{json.dumps(self.task_manager.get_statistics(), ensure_ascii=False, indent=2)}

你可以使用 MCP 工具来执行文件操作等任务。
"""
        
        # 调用模型
        print(f"\n{UI.BLUE}[Leader]{UI.END} ", end="", flush=True)
        response, tool_calls = await self.model.call_async(user_input, system_prompt, tools)
        
        # 处理工具调用循环
        if tool_calls:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
            await self._handle_tool_calls_loop(tool_calls, messages, tools)
        
        # 显示任务状态
        self.task_manager.show_progress()
    
    async def _handle_tool_calls_loop(self, tool_calls: List[Dict], messages: List[Dict], tools: List[Dict]):
        """
        处理工具调用循环
        
        Args:
            tool_calls: 工具调用列表
            messages: 消息历史
            tools: 工具定义
        """
        max_iterations = 20
        iteration = 0
        
        while tool_calls and iteration < max_iterations:
            iteration += 1
            
            # 添加助手响应
            messages.append({
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
                
                # MCP 工具
                if "__" in name:
                    result = await self.mcp_manager.call(name, args)
                # 进化工具
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
                else:
                    result = f"未知工具: {name}"
                
                # 添加工具结果
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": name,
                    "content": result
                })
            
            # 继续对话
            print(f"{UI.CYAN}[继续]{UI.END} ", end="", flush=True)
            response, tool_calls = await self.model.call_with_messages(messages, tools, stream=True)
            
            if response:
                messages.append({"role": "assistant", "content": response})
    
    def _get_evolution_tools(self) -> List[Dict]:
        """获取进化工具定义"""
        return [
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
        """执行循环"""
        max_iterations = 20
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
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
