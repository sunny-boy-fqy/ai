"""
AI CLI 自动工作模式
Leader AI 自动规划并执行任务
使用 MCP 工具进行实际的文件操作
"""

import os
import sys
import json
import asyncio
import subprocess
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.constants import USER_AI_DIR, ensure_dirs
from tools.ui import UI
from tools.plugin import MCPToolManager


# 任务状态定义
TASK_STATUS = {
    "pending": "等待执行",
    "ready": "依赖已满足，可以开始",
    "in_progress": "正在执行",
    "completed": "已完成",
    "failed": "执行失败",
    "blocked": "被阻塞"
}


class TaskItem:
    """单个任务项"""
    def __init__(self, data: dict = None):
        self.id: str = ""
        self.title: str = ""
        self.description: str = ""
        self.status: str = "pending"
        self.assigned_to: str = ""
        self.dependencies: List[str] = []
        self.priority: int = 1
        self.created_at: str = ""
        self.started_at: str = ""
        self.completed_at: str = ""
        self.result_summary: str = ""
        self.git_commit: str = ""
        
        if data:
            self.from_dict(data)
    
    def from_dict(self, data: dict):
        self.id = data.get("id", "")
        self.title = data.get("title", "")
        self.description = data.get("description", "")
        self.status = data.get("status", "pending")
        self.assigned_to = data.get("assigned_to", "")
        self.dependencies = data.get("dependencies", [])
        self.priority = data.get("priority", 1)
        self.created_at = data.get("created_at", "")
        self.started_at = data.get("started_at", "")
        self.completed_at = data.get("completed_at", "")
        self.result_summary = data.get("result_summary", "")
        self.git_commit = data.get("git_commit", "")
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "dependencies": self.dependencies,
            "priority": self.priority,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result_summary": self.result_summary,
            "git_commit": self.git_commit
        }


class GitManager:
    """Git 版本管理"""
    
    @classmethod
    def init_repo(cls, work_dir: str) -> bool:
        """初始化git仓库"""
        git_dir = os.path.join(work_dir, ".git")
        if os.path.exists(git_dir):
            return True
        
        try:
            result = subprocess.run(
                ["git", "init"],
                cwd=work_dir,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            UI.error(f"Git初始化失败: {e}")
            return False
    
    @classmethod
    def commit(cls, work_dir: str, message: str) -> Optional[str]:
        """提交更改，返回commit hash"""
        try:
            # 添加所有更改
            subprocess.run(
                ["git", "add", "."],
                cwd=work_dir,
                capture_output=True
            )
            
            # 检查是否有更改
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=work_dir,
                capture_output=True,
                text=True
            )
            if not result.stdout.strip():
                return None  # 没有更改
            
            # 提交
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=work_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # 获取commit hash
                hash_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=work_dir,
                    capture_output=True,
                    text=True
                )
                if hash_result.returncode == 0:
                    return hash_result.stdout.strip()
            return None
        except Exception as e:
            UI.error(f"Git提交失败: {e}")
            return None
    
    @classmethod
    def get_last_commit(cls, work_dir: str) -> Optional[str]:
        """获取最后一次提交的hash"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=work_dir,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except:
            return None


class WorkflowManager:
    """工作流管理器"""
    
    def __init__(self, work_dir: str):
        self.work_dir = work_dir
        self.ai_dir = os.path.join(work_dir, ".ai")
        self.tasks_file = os.path.join(self.ai_dir, "tasks.json")
        self.tasks: List[TaskItem] = []
        self.metadata: dict = {}
        self._load()
    
    def _load(self):
        """加载任务文件"""
        if os.path.exists(self.tasks_file):
            try:
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.metadata = data.get("metadata", {})
                    self.tasks = [TaskItem(t) for t in data.get("tasks", [])]
            except Exception as e:
                UI.error(f"加载任务文件失败: {e}")
    
    def save(self):
        """保存任务文件"""
        os.makedirs(self.ai_dir, exist_ok=True)
        
        data = {
            "metadata": self.metadata,
            "tasks": [t.to_dict() for t in self.tasks],
            "updated_at": datetime.now().isoformat()
        }
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_pending_tasks(self) -> List[TaskItem]:
        """获取待处理的任务（依赖已完成的）"""
        completed_ids = {t.id for t in self.tasks if t.status == "completed"}
        pending = []
        for task in self.tasks:
            if task.status == "pending":
                # 检查依赖是否都已完成
                if all(dep in completed_ids for dep in task.dependencies):
                    pending.append(task)
        return sorted(pending, key=lambda x: x.priority, reverse=True)
    
    def get_task_by_id(self, task_id: str) -> Optional[TaskItem]:
        """通过ID获取任务"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def get_progress(self) -> Tuple[int, int, float]:
        """获取进度 (已完成数, 总数, 百分比)"""
        completed = len([t for t in self.tasks if t.status == "completed"])
        total = len(self.tasks)
        pct = (completed / total * 100) if total > 0 else 0
        return completed, total, pct
    
    def show_progress(self):
        """显示当前进度"""
        completed, total, pct = self.get_progress()
        
        # 进度条
        bar_length = 30
        filled = int(bar_length * completed / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_length - filled)
        
        print(f"\n{UI.CYAN}📊 任务进度: {bar} {pct:.1f}% ({completed}/{total}){UI.END}")
        
        # 显示当前正在执行的任务
        in_progress = [t for t in self.tasks if t.status == "in_progress"]
        if in_progress:
            print(f"\n{UI.YELLOW}🔄 正在执行:{UI.END}")
            for t in in_progress:
                print(f"   {t.id}: {t.title}")
        
        # 显示待执行任务
        pending = self.get_pending_tasks()
        if pending and len(pending) <= 5:
            print(f"\n{UI.DIM}⏳ 即将执行:{UI.END}")
            for t in pending[:5]:
                print(f"   {t.id}: {t.title}")
        
        print()
    
    def show_tasks_table(self):
        """显示任务表格"""
        print(f"\n{UI.BOLD}📋 任务列表:{UI.END}")
        print("-" * 60)
        
        for task in self.tasks:
            status_icons = {
                "pending": "⏳",
                "ready": "📌",
                "in_progress": "🔄",
                "completed": "✅",
                "failed": "❌",
                "blocked": "🚫"
            }
            icon = status_icons.get(task.status, "❓")
            
            # 状态颜色
            status_color = {
                "pending": UI.DIM,
                "ready": UI.BLUE,
                "in_progress": UI.YELLOW,
                "completed": UI.GREEN,
                "failed": UI.RED,
                "blocked": UI.RED
            }.get(task.status, UI.DIM)
            
            print(f"{icon} [{task.id}] {task.title}")
            print(f"   状态: {status_color}{TASK_STATUS.get(task.status, task.status)}{UI.END}")
            if task.dependencies:
                print(f"   依赖: {', '.join(task.dependencies)}")
            print()
        
        self.show_progress()


class LeaderWorkerEngine:
    """Leader-Worker 自动工作引擎"""
    
    @classmethod
    def _load_prompts(cls) -> Tuple[str, str]:
        """加载 Leader 和 Worker 的提示模板"""
        # 加载 Leader 提示
        leader_file = os.path.join(USER_AI_DIR, "templates", "README_for_leader.md")
        leader_prompt = ""
        if os.path.exists(leader_file):
            with open(leader_file, 'r', encoding='utf-8') as f:
                leader_prompt = f.read()
        
        # 加载 Worker 提示
        worker_file = os.path.join(USER_AI_DIR, "templates", "README_for_worker.md")
        worker_prompt = ""
        if os.path.exists(worker_file):
            with open(worker_file, 'r', encoding='utf-8') as f:
                worker_prompt = f.read()
        
        return leader_prompt, worker_prompt
    
    @classmethod
    async def run_auto(cls, work_dir: str, client, model: str):
        """
        自动工作模式：Leader AI 规划任务，Worker AI 执行任务
        使用 MCP 工具进行实际操作
        """
        # 初始化工作流
        wf = WorkflowManager(work_dir)
        
        # 初始化 git
        GitManager.init_repo(work_dir)
        
        # 加载提示模板
        leader_prompt, worker_prompt = cls._load_prompts()
        
        # 询问用户任务
        print(f"\n{UI.BOLD}请描述您要完成的任务:{UI.END}")
        user_task = input("> ").strip()
        
        if not user_task:
            UI.error("任务描述不能为空")
            return
        
        # ===== 第一阶段：Leader 规划任务 =====
        UI.section("🎯 Leader AI 正在分析任务...")
        UI.info(f"任务: {user_task[:100]}...")
        
        # 构建 Leader 系统提示
        leader_system = f"""你是 Leader AI，负责任务规划和协调。

你的工作目录是: {work_dir}

{leader_prompt}

重要说明：
- 你必须使用 JSON 格式输出任务列表
- 每个任务必须包含：id, title, description, priority, dependencies
- 任务应该是具体的、可执行的
- 合理的任务拆分很重要，每个任务应该能在一次 AI 调用中完成
- 输出格式必须是有效的 JSON 数组

请为用户任务创建详细的执行计划。"""
        
        # 调用 Leader AI
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": leader_system},
                    {"role": "user", "content": f"请为以下任务创建详细的执行计划:\n\n{user_task}"}
                ],
                temperature=0.3
            )
            
            leader_response = response.choices[0].message.content
            print(f"\n{UI.CYAN}Leader 分析完成{UI.END}")
            
            # 解析任务
            tasks = cls._parse_tasks(leader_response)
            
            if not tasks:
                UI.error("无法解析任务列表")
                print("原始响应:", leader_response[:500])
                return
            
            # 保存任务到工作流
            wf.metadata = {
                "name": user_task[:50],
                "description": user_task,
                "created_at": datetime.now().isoformat(),
                "status": "in_progress",
                "lead_model": model
            }
            
            for i, task_data in enumerate(tasks, 1):
                task = TaskItem()
                task.id = f"task_{i:03d}"
                task.title = task_data.get("title", f"任务{i}")
                task.description = task_data.get("description", "")
                task.priority = task_data.get("priority", 3)
                task.dependencies = task_data.get("dependencies", [])
                task.status = "pending"
                task.created_at = datetime.now().isoformat()
                wf.tasks.append(task)
            
            wf.save()
            
            # 提交初始计划
            GitManager.commit(work_dir, f"Leader: Created task plan with {len(tasks)} tasks")
            
            UI.success(f"✅ 已创建 {len(tasks)} 个子任务")
            
            # 显示任务表格
            wf.show_tasks_table()
            
        except Exception as e:
            UI.error(f"Leader 规划失败: {e}")
            return
        
        # ===== 第二阶段：Worker 执行任务 =====
        max_iterations = len(wf.tasks) * 2  # 防止无限循环
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # 获取待处理任务
            pending = wf.get_pending_tasks()
            
            if not pending:
                # 检查是否有失败的任务
                failed = [t for t in wf.tasks if t.status == "failed"]
                if failed:
                    UI.error(f"有 {len(failed)} 个任务失败")
                    break
                else:
                    UI.success("🎉 所有任务已完成!")
                    break
            
            # 选择下一个任务
            current_task = pending[0]
            
            # ===== Worker 执行任务 =====
            UI.section(f"🔧 Worker 执行任务: {current_task.id}")
            print(f"任务: {current_task.title}")
            print(f"描述: {current_task.description[:200]}...")
            
            # 更新任务状态
            current_task.status = "in_progress"
            current_task.started_at = datetime.now().isoformat()
            wf.save()
            
            # 构建 Worker 上下文
            context = cls._build_context(wf, current_task)
            
            # 构建 Worker 系统提示
            worker_system = f"""你是 Worker AI，负责执行具体的开发任务。

你的工作目录是: {work_dir}
当前任务目录: {work_dir}

{worker_prompt}

重要说明：
- 你可以使用 MCP 工具来操作文件系统和执行命令
- 所有文件操作都在 {work_dir} 目录下进行
- 完成任务后，报告你做了什么以及结果
- 如果遇到问题，说明原因和建议的解决方案
- 报告格式：简短描述完成的工作和结果"""
            
            # 调用 Worker AI
            try:
                # 记录开始前的 commit
                start_commit = GitManager.get_last_commit(work_dir)
                
                # 初始化 MCP 工具
                mgr = MCPToolManager()
                await mgr.initialize()
                tools = await mgr.get_tools()
                
                # 添加进化工具
                tools.extend(cls._get_evolution_tools())
                
                # 第一次调用：让 Worker 分析任务
                messages = [
                    {"role": "system", "content": worker_system},
                    {"role": "user", "content": f"""请执行以下任务：

任务ID: {current_task.id}
任务标题: {current_task.title}
任务描述: {current_task.description}

上下文信息：
{context}

请开始执行任务。使用可用的 MCP 工具来完成工作。"""}
                ]
                
                # 执行对话循环
                result = await cls._execute_with_tools(
                    client, model, messages, tools, mgr, work_dir
                )
                
                # 提交更改
                commit_msg = f"Worker: Completed {current_task.id} - {current_task.title}"
                commit_hash = GitManager.commit(work_dir, commit_msg)
                
                # 更新任务状态
                current_task.status = "completed"
                current_task.completed_at = datetime.now().isoformat()
                current_task.result_summary = result[:500] if result else "任务完成"
                if commit_hash:
                    current_task.git_commit = commit_hash
                
                wf.save()
                
                UI.success(f"✅ 任务 {current_task.id} 完成")
                
                # 显示进度
                wf.show_progress()
                
            except Exception as e:
                UI.error(f"任务执行失败: {e}")
                current_task.status = "failed"
                current_task.result_summary = f"执行失败: {str(e)}"
                wf.save()
                
                # 询问是否继续
                if not UI.confirm("任务执行失败，是否继续下一个任务？"):                    
                    break
        
        # ===== 完成 =====
        UI.section("🏁 执行完成")
        wf.show_tasks_table()
        
        # 更新元数据
        wf.metadata["status"] = "completed"
        wf.metadata["completed_at"] = datetime.now().isoformat()
        wf.save()
    
    @classmethod
    async def _execute_with_tools(cls, client, model, messages, tools, mgr, work_dir) -> str:
        """使用工具执行对话"""
        full_response = ""
        
        while True:
            try:
                res = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools if tools else None,
                    stream=False
                )
                
                response = res.choices[0].message
                full_response = response.content or ""
                tool_calls = response.tool_calls or []
                
                if not tool_calls:
                    return full_response
                
                # 处理工具调用
                messages.append({
                    "role": "assistant",
                    "content": full_response or None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in tool_calls
                    ]
                })
                
                for tc in tool_calls:
                    result = await cls._handle_tool_call(tc, mgr, work_dir)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.function.name,
                        "content": result
                    })
                    
            except Exception as e:
                return full_response + f"\n\n[执行出错: {e}]"
    
    @classmethod
    async def _handle_tool_call(cls, tc, mgr, work_dir) -> str:
        """处理工具调用"""
        name = tc.function.name
        try:
            args = json.loads(tc.function.arguments)
        except:
            args = {}
        
        UI.info(f"🔧 调用工具: {name}")
        
        # 进化工具
        if name == "search_plugin":
            from tools.plugin import PluginManager
            results = PluginManager.search(args.get("query", ""))
            return cls._format_search_results(results)
        
        elif name == "install_plugin":
            from tools.plugin import PluginManager
            success = await PluginManager.install(args.get("name", ""))
            return "安装成功" if success else "安装失败"
        
        elif name == "analyze_gap":
            return "分析完成"
        
        # MCP 工具
        elif "__" in name:
            return await mgr.call(name, args)
        
        return "未知工具"
    
    @classmethod
    def _get_evolution_tools(cls) -> List[dict]:
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
    
    @classmethod
    def _build_context(cls, wf: WorkflowManager, current_task: TaskItem) -> str:
        """构建任务执行上下文"""
        context_parts = []
        
        # 项目信息
        context_parts.append(f"项目名称: {wf.metadata.get('name', 'Unknown')}")
        context_parts.append(f"项目描述: {wf.metadata.get('description', '')}")
        context_parts.append("")
        
        # 已完成的任务
        completed_tasks = [t for t in wf.tasks if t.status == "completed"]
        if completed_tasks:
            context_parts.append("=== 已完成的任务 ===")
            for t in completed_tasks:
                context_parts.append(f"- {t.id}: {t.title}")
                if t.result_summary:
                    context_parts.append(f"  结果: {t.result_summary[:200]}")
            context_parts.append("")
        
        # 当前任务
        context_parts.append("=== 当前任务 ===")
        context_parts.append(f"ID: {current_task.id}")
        context_parts.append(f"标题: {current_task.title}")
        context_parts.append(f"描述: {current_task.description}")
        context_parts.append(f"优先级: {current_task.priority}")
        
        if current_task.dependencies:
            context_parts.append("\n依赖的任务结果:")
            for dep_id in current_task.dependencies:
                dep_task = wf.get_task_by_id(dep_id)
                if dep_task and dep_task.result_summary:
                    context_parts.append(f"- {dep_id}: {dep_task.result_summary[:300]}")
        
        return "\n".join(context_parts)
    
    @classmethod
    def _parse_tasks(cls, response: str) -> List[dict]:
        """从AI响应中解析任务列表"""
        import re
        
        # 尝试提取JSON代码块
        patterns = [
            r'```json\s*(\[\s*\{.*?\}\s*\])\s*```',
            r'```\s*(\[\s*\{.*?\}\s*\])\s*```',
            r'(\[\s*\{\s*"id".*?"title".*?\}\s*\])'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except:
                    pass
        
        # 尝试直接解析整个响应
        try:
            data = json.loads(response)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "tasks" in data:
                return data["tasks"]
        except:
            pass
        
        return []
    
    @classmethod
    def _format_search_results(cls, results: list) -> str:
        """格式化搜索结果"""
        if not results:
            return "未找到匹配插件"
        
        lines = ["找到以下插件：\n"]
        for p in results[:10]:
            lines.append(f"- {p.name}: {p.description}")
            if p.required_env:
                lines.append(f"  需要环境变量: {', '.join(p.required_env)}")
        
        return "\n".join(lines)
