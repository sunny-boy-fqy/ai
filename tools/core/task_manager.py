"""
AI CLI 任务管理器
管理任务的创建、更新、查询
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional
from ..ui import UI


class TaskManager:
    """任务管理器"""
    
    def __init__(self, ai_dir: str):
        """
        初始化任务管理器
        
        Args:
            ai_dir: .ai 目录路径
        """
        self.ai_dir = ai_dir
        self.tasks_file = os.path.join(ai_dir, "tasks.json")
        self.tasks_data = self._load_tasks()
    
    def _load_tasks(self) -> Dict:
        """加载任务数据"""
        if not os.path.exists(self.tasks_file):
            return self._create_empty_tasks()
        
        try:
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return self._create_empty_tasks()
    
    def _create_empty_tasks(self) -> Dict:
        """创建空的任务数据"""
        return {
            "project_name": os.path.basename(os.path.dirname(self.ai_dir)),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "idle",
            "current_task": None,
            "tasks": [],
            "statistics": {
                "total": 0,
                "pending": 0,
                "in_progress": 0,
                "completed": 0,
                "failed": 0
            }
        }
    
    def _save_tasks(self):
        """保存任务数据"""
        self.tasks_data["updated_at"] = datetime.now().isoformat()
        self._update_statistics()
        
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(self.tasks_data, f, ensure_ascii=False, indent=2)
    
    def _update_statistics(self):
        """更新统计数据"""
        tasks = self.tasks_data.get("tasks", [])
        stats = {
            "total": len(tasks),
            "pending": sum(1 for t in tasks if t.get("status") == "pending"),
            "in_progress": sum(1 for t in tasks if t.get("status") == "in_progress"),
            "completed": sum(1 for t in tasks if t.get("status") == "completed"),
            "failed": sum(1 for t in tasks if t.get("status") == "failed"),
        }
        self.tasks_data["statistics"] = stats
    
    def create_task(
        self,
        title: str,
        description: str,
        task_type: str = "code",
        priority: int = 3,
        dependencies: List[str] = None,
        files_to_modify: List[str] = None,
        acceptance_criteria: List[str] = None,
    ) -> Dict:
        """
        创建新任务
        
        Args:
            title: 任务标题
            description: 任务描述
            task_type: 任务类型 (code|doc|config|test|review|refactor|fix)
            priority: 优先级 (1-5)
            dependencies: 依赖的任务ID列表
            files_to_modify: 需要修改的文件列表
            acceptance_criteria: 验收标准
            
        Returns:
            创建的任务字典
        """
        task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.tasks_data['tasks']) + 1}"
        
        task = {
            "id": task_id,
            "title": title,
            "description": description,
            "type": task_type,
            "priority": priority,
            "status": "pending",
            "dependencies": dependencies or [],
            "assigned_to": None,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "files_to_modify": files_to_modify or [],
            "acceptance_criteria": acceptance_criteria or [],
            "result_summary": None,
            "error_log": None,
            "git_commit": None,
            "notes": []
        }
        
        self.tasks_data["tasks"].append(task)
        self._save_tasks()
        
        return task
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务"""
        for task in self.tasks_data.get("tasks", []):
            if task.get("id") == task_id:
                return task
        return None
    
    def update_task(self, task_id: str, **kwargs) -> bool:
        """
        更新任务
        
        Args:
            task_id: 任务ID
            **kwargs: 要更新的字段
            
        Returns:
            是否成功
        """
        task = self.get_task(task_id)
        if not task:
            return False
        
        for key, value in kwargs.items():
            if key in task:
                task[key] = value
        
        self._save_tasks()
        return True
    
    def set_task_status(self, task_id: str, status: str, result: str = None, error: str = None) -> bool:
        """
        设置任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            result: 结果摘要
            error: 错误日志
            
        Returns:
            是否成功
        """
        updates = {"status": status}
        
        if status == "in_progress":
            updates["started_at"] = datetime.now().isoformat()
        elif status == "completed":
            updates["completed_at"] = datetime.now().isoformat()
            if result:
                updates["result_summary"] = result
        elif status == "failed":
            updates["completed_at"] = datetime.now().isoformat()
            if error:
                updates["error_log"] = error
        
        return self.update_task(task_id, **updates)
    
    def get_pending_tasks(self) -> List[Dict]:
        """获取待处理的任务"""
        return [
            t for t in self.tasks_data.get("tasks", [])
            if t.get("status") == "pending"
        ]
    
    def get_ready_tasks(self) -> List[Dict]:
        """
        获取可以执行的任务（依赖已满足）
        
        Returns:
            可执行的任务列表
        """
        tasks = self.tasks_data.get("tasks", [])
        ready = []
        
        # 构建任务ID到状态的映射
        task_status = {t["id"]: t["status"] for t in tasks}
        
        for task in tasks:
            if task["status"] != "pending":
                continue
            
            # 检查依赖是否全部完成
            dependencies = task.get("dependencies", [])
            all_deps_completed = all(
                task_status.get(dep_id) == "completed"
                for dep_id in dependencies
            )
            
            if all_deps_completed:
                ready.append(task)
        
        # 按优先级排序
        ready.sort(key=lambda t: t.get("priority", 3))
        
        return ready
    
    def get_in_progress_tasks(self) -> List[Dict]:
        """获取进行中的任务"""
        return [
            t for t in self.tasks_data.get("tasks", [])
            if t.get("status") == "in_progress"
        ]
    
    def get_next_task(self) -> Optional[Dict]:
        """获取下一个要执行的任务"""
        ready = self.get_ready_tasks()
        return ready[0] if ready else None
    
    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务"""
        return self.tasks_data.get("tasks", [])
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return self.tasks_data.get("statistics", {})
    
    def show_progress(self):
        """显示进度"""
        stats = self.get_statistics()
        tasks = self.get_all_tasks()
        
        UI.section("任务进度")
        
        # 统计信息
        total = stats.get("total", 0)
        completed = stats.get("completed", 0)
        in_progress = stats.get("in_progress", 0)
        pending = stats.get("pending", 0)
        failed = stats.get("failed", 0)
        
        print()
        print(f"  总计: {total} | 完成: {UI.GREEN}{completed}{UI.END} | "
              f"进行中: {UI.CYAN}{in_progress}{UI.END} | "
              f"待处理: {UI.YELLOW}{pending}{UI.END} | "
              f"失败: {UI.RED}{failed}{UI.END}")
        print()
        
        if not tasks:
            UI.info("暂无任务")
            return
        
        # 进度条
        if total > 0:
            progress = completed / total
            bar_length = 40
            filled = int(bar_length * progress)
            bar = f"{'█' * filled}{'░' * (bar_length - filled)}"
            print(f"  进度: [{UI.GREEN}{bar}{UI.END}] {progress*100:.1f}%")
            print()
        
        # 任务列表
        print("  任务列表:")
        print()
        
        for task in tasks:
            status_icons = {
                "pending": f"{UI.YELLOW}○{UI.END}",
                "in_progress": f"{UI.CYAN}◐{UI.END}",
                "completed": f"{UI.GREEN}●{UI.END}",
                "failed": f"{UI.RED}✗{UI.END}",
            }
            
            icon = status_icons.get(task["status"], "○")
            title = task.get("title", "无标题")
            task_id = task.get("id", "")
            
            # 当前任务高亮
            if task["status"] == "in_progress":
                print(f"  {icon} {UI.BOLD}{task_id}: {title}{UI.END}")
                if task.get("description"):
                    desc = task["description"][:80]
                    print(f"    {UI.DIM}{desc}...{UI.END}")
            else:
                print(f"  {icon} {task_id}: {title}")
            
            # 显示错误
            if task["status"] == "failed" and task.get("error_log"):
                error_preview = task["error_log"][:60]
                print(f"    {UI.RED}错误: {error_preview}...{UI.END}")
        
        print()
    
    def set_project_status(self, status: str):
        """设置项目状态"""
        self.tasks_data["status"] = status
        self._save_tasks()
    
    def add_note(self, task_id: str, note: str, author: str = "user") -> bool:
        """
        添加任务备注
        
        Args:
            task_id: 任务ID
            note: 备注内容
            author: 作者
            
        Returns:
            是否成功
        """
        task = self.get_task(task_id)
        if not task:
            return False
        
        if "notes" not in task:
            task["notes"] = []
        
        task["notes"].append({
            "timestamp": datetime.now().isoformat(),
            "author": author,
            "content": note
        })
        
        self._save_tasks()
        return True
    
    def clear_completed_tasks(self):
        """清理已完成的任务"""
        self.tasks_data["tasks"] = [
            t for t in self.tasks_data.get("tasks", [])
            if t.get("status") != "completed"
        ]
        self._save_tasks()
        UI.success("已清理完成的任务")
    
    def reset_all_tasks(self):
        """重置所有任务状态"""
        for task in self.tasks_data.get("tasks", []):
            task["status"] = "pending"
            task["started_at"] = None
            task["completed_at"] = None
            task["assigned_to"] = None
        
        self._save_tasks()
        UI.success("已重置所有任务")
