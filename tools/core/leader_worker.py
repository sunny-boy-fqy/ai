"""
AI CLI Leader-Worker 核心
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
        """
        初始化模型接口
        
        Args:
            config: 模型配置 {
                "provider": str,
                "model": str,
                "api_key": str,
                "base_url": str
            }
        """
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
        """
        调用模型
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            tools: 工具定义
            stream: 是否流式输出
            
        Returns:
            (响应文本, 工具调用列表)
        """
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
        """
        清理模型输出，移除异常的 token 标记
        
        Args:
            content: 原始输出
            
        Returns:
            清理后的输出
        """
        if not content:
            return content
        
        # 移除常见的异常 token 标记
        patterns = [
            r'<\|tool_calls_section_begin\|>',
            r'<\|tool_calls_section_end\|>',
            r'<\|tool_call_begin\|>',
            r'<\|tool_call_end\|>',
            r'<\|tool_call_argument_begin\|>',
            r'<\|tool_call_argument_end\|>',
            r'<\|tool_call_argument\|>',
            r'<\|.*?\|>',  # 其他类似的标记
        ]
        
        cleaned = content
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned)
        
        # 移除 "functions.xxx:n" 这样的残留片段
        cleaned = re.sub(r'functions\.\w+:\d+\s*', '', cleaned)
        
        # 移除孤立的 JSON 对象片段（通常是工具调用参数残留）
        # 匹配模式：{"xxx": "yyy", ...} 格式的单行 JSON
        cleaned = re.sub(r'\{\s*"[^"]+"\s*:\s*"[^"]*"[^}]*\}\s*', '', cleaned)
        
        # 移除多余空白
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def _parse_tool_calls_from_text(self, content: str) -> List[Dict]:
        """
        从文本中解析工具调用（当模型不返回结构化工具调用时）
        
        Args:
            content: 模型输出文本
            
        Returns:
            工具调用列表
        """
        tool_calls = []
        
        # 尝试从文本中提取 JSON 工具调用
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
        
        # 模式2: JSON 代码块中的工具调用
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
        """
        异步调用模型（支持流式输出）
        """
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
                        # 清理异常 token 标记后再输出
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
                
                print()  # 换行
                
                # 清理输出内容
                full_content = self._clean_model_output(full_content)
                
                # 如果没有结构化的工具调用，尝试从文本中解析
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
                
                # 如果没有结构化的工具调用，尝试从文本中解析
                if not tool_calls and tools:
                    tool_calls = self._parse_tool_calls_from_text(content)
                
                return content, tool_calls
                
        except Exception as e:
            return f"调用失败: {e}", []


class LeaderAI:
    """
    Leader AI
    - 接收用户指令
    - 规划和拆分任务
    - 分配任务给 Worker
    - 监控进度
    - 与用户交互
    """
    
    def __init__(self, ai_dir: str):
        """
        初始化 Leader AI
        
        Args:
            ai_dir: .ai 目录路径
        """
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
        
        # 读取 README 指南
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
        # 先从模板目录读取
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
        
        # 创建输入处理器
        input_handler = InputHandler("", allow_multiline=True)
        
        while True:
            try:
                # 使用多行输入
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
        """
        处理用户输入
        
        Args:
            user_input: 用户输入
        """
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
"""
        
        # 调用模型
        print(f"\n{UI.BLUE}[Leader]{UI.END} ", end="", flush=True)
        response, tool_calls = await self.model.call_async(user_input, system_prompt)
        
        # 更新任务状态
        self.task_manager.show_progress()
    
    async def plan_tasks(self, user_request: str) -> bool:
        """
        规划任务
        
        Args:
            user_request: 用户需求描述
            
        Returns:
            是否成功
        """
        if not self.model:
            UI.error("模型未初始化")
            return False
        
        UI.info("正在分析需求并规划任务...")
        
        # 构建规划提示
        system_prompt = f"""你是任务规划专家。

{self.leader_guide}

请根据用户需求，创建详细的任务列表。每个任务应该是：
- 单一职责
- 可执行
- 有明确的完成标准

返回 JSON 格式的任务列表，包含以下字段：
- title: 任务标题
- description: 详细描述
- type: 任务类型 (code|doc|config|test|review|refactor|fix)
- priority: 优先级 (1-5, 1最高)
- dependencies: 依赖的任务ID列表
- files_to_modify: 需要修改的文件列表
- acceptance_criteria: 验收标准
"""
        
        response, _ = self.model.call(user_request, system_prompt)
        
        # 解析响应，创建任务
        # TODO: 更智能的解析
        tasks = self._parse_tasks_from_response(response)
        
        for task_data in tasks:
            self.task_manager.create_task(**task_data)
        
        UI.success(f"已创建 {len(tasks)} 个任务")
        self.task_manager.show_progress()
        
        return True
    
    def _parse_tasks_from_response(self, response: str) -> List[Dict]:
        """从模型响应中解析任务"""
        # 尝试提取 JSON
        tasks = []
        
        try:
            # 尝试找到 JSON 块
            import re
            
            # 查找 ```json ... ``` 块
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
            
            # 如果没找到 JSON 块，尝试直接解析
            if not tasks:
                data = json.loads(response)
                if isinstance(data, list):
                    tasks = data
                elif isinstance(data, dict) and "tasks" in data:
                    tasks = data["tasks"]
                    
        except json.JSONDecodeError:
            # 如果解析失败，创建一个简单任务
            tasks = [{
                "title": "执行用户需求",
                "description": response,
                "type": "code",
                "priority": 3,
                "dependencies": [],
            }]
        
        return tasks
    
    async def assign_task_to_worker(self, task: Dict) -> Tuple[bool, str]:
        """
        分配任务给 Worker
        
        Args:
            task: 任务字典
            
        Returns:
            (是否成功, 结果/错误信息)
        """
        if not self.worker_model:
            return False, "Worker 模型未配置"
        
        # 标记任务为进行中
        self.task_manager.set_task_status(task["id"], "in_progress")
        
        # 创建 Worker 实例
        worker = WorkerAI(
            ai_dir=self.ai_dir,
            task=task,
            model_interface=self.worker_model,
            mcp_manager=self.mcp_manager,
            leader=self
        )
        
        # 执行任务
        success, result = await worker.execute()
        
        # 更新任务状态
        if success:
            self.task_manager.set_task_status(task["id"], "completed", result=result)
        else:
            self.task_manager.set_task_status(task["id"], "failed", error=result)
        
        return success, result
    
    def request_user_help(self, message: str) -> str:
        """
        向用户请求帮助
        
        Args:
            message: 请求消息
            
        Returns:
            用户响应
        """
        UI.section("需要您的帮助")
        print(f"\n  {message}\n")
        
        response = UI.input("请提供指导或帮助")
        return response
    
    def update_progress_display(self):
        """更新进度显示"""
        # 清屏并显示进度
        if sys.platform != "win32":
            os.system('clear')
        else:
            os.system('cls')
        
        self.task_manager.show_progress()


class WorkerAI:
    """
    Worker AI
    - 执行具体任务
    - 自动使用 MCP 插件
    - 不与用户交互
    - 出错时与 Leader 沟通
    """
    
    def __init__(
        self,
        ai_dir: str,
        task: Dict,
        model_interface: ModelInterface,
        mcp_manager: MCPToolManager,
        leader: LeaderAI
    ):
        """
        初始化 Worker AI
        
        Args:
            ai_dir: .ai 目录
            task: 要执行的任务
            model_interface: 模型接口
            mcp_manager: MCP 工具管理器
            leader: Leader AI 引用（用于报告错误）
        """
        self.ai_dir = ai_dir
        self.root_dir = os.path.dirname(ai_dir)
        self.task = task
        self.model = model_interface
        self.mcp_manager = mcp_manager
        self.leader = leader
        
        # 加载指南
        self.worker_guide = self._load_guide()
        
        # 工具定义
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
        """
        执行任务
        
        Returns:
            (是否成功, 结果摘要/错误信息)
        """
        try:
            # 获取 MCP 工具
            self.tools = await self.mcp_manager.get_tools()
            
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
"""
            
            user_prompt = f"请执行任务: {self.task.get('title')}\n\n{self.task.get('description')}"
            
            # 执行任务循环
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            return await self._execution_loop(messages)
            
        except Exception as e:
            return False, f"执行异常: {e}"
    
    async def _execution_loop(self, messages: List[Dict]) -> Tuple[bool, str]:
        """
        执行循环（处理工具调用）
        
        Args:
            messages: 消息历史
            
        Returns:
            (是否成功, 结果)
        """
        max_iterations = 20
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # 调用模型
            response, tool_calls = await self.model.call_async(
                messages[-1]["content"],
                messages[0]["content"],
                self.tools,
                stream=True
            )
            
            # 添加响应到消息历史
            messages.append({
                "role": "assistant",
                "content": response,
                "tool_calls": tool_calls if tool_calls else None
            })
            
            # 如果没有工具调用，任务完成
            if not tool_calls:
                return True, response
            
            # 处理工具调用
            all_success = True
            error_messages = []
            
            for tc in tool_calls:
                result = await self._handle_tool_call(tc)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": tc["function"]["name"],
                    "content": result
                })
                
                # 检查是否出错
                if "ERROR" in result or "失败" in result:
                    all_success = False
                    error_messages.append(result)
            
            # 如果多次失败，报告给 Leader
            if not all_success and len(error_messages) > 3:
                return False, "\n".join(error_messages)
        
        return False, "超过最大迭代次数"
    
    async def _handle_tool_call(self, tc: Dict) -> str:
        """
        处理工具调用
        
        Args:
            tc: 工具调用字典
            
        Returns:
            工具执行结果
        """
        name = tc["function"]["name"]
        
        try:
            args = json.loads(tc["function"]["arguments"])
        except:
            args = {}
        
        UI.info(f"Worker 执行: {name}")
        
        # MCP 工具调用
        if "__" in name:
            return await self.mcp_manager.call(name, args)
        
        # 内置工具
        if name == "report_error_to_leader":
            return self._report_to_leader(args.get("error", ""))
        
        return f"未知工具: {name}"
    
    def _report_to_leader(self, error: str) -> str:
        """
        向 Leader 报告错误
        
        Args:
            error: 错误信息
            
        Returns:
            Leader 的响应
        """
        # 记录错误到任务
        self.leader.task_manager.add_note(
            self.task["id"],
            f"Worker 报告错误: {error}",
            "worker"
        )
        
        # Leader 会决定如何处理
        return f"已将错误报告给 Leader: {error}"


async def run_leader_worker_session(ai_dir: str):
    """
    启动 Leader-Worker 会话
    
    Args:
        ai_dir: .ai 目录路径
    """
    leader = LeaderAI(ai_dir)
    await leader.start_session()
