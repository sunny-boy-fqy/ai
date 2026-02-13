"""
AI CLI 任务管理
支持长期任务、定时任务、计划任务
"""

import os
import json
import time
import signal
import asyncio
import subprocess
from datetime import datetime
from typing import List, Dict, Optional
from threading import Thread
from .constants import CONFIG_DIR, ensure_dirs
from .ui import UI


TASK_FILE = os.path.join(CONFIG_DIR, "tasks.json")
TASK_LOG_DIR = os.path.join(CONFIG_DIR, "task_logs")
PID_FILE = os.path.join(CONFIG_DIR, "task_daemon.pid")


class Task:
    """任务"""
    def __init__(self):
        self.id: str = ""
        self.type: str = ""  # once, interval, schedule
        self.command: str = ""
        self.interval: int = 0  # 秒，用于interval类型
        self.schedule: str = ""  # cron格式，用于schedule类型
        self.status: str = "pending"  # pending, running, completed, failed
        self.created: str = ""
        self.last_run: str = ""
        self.next_run: str = ""


class TaskManager:
    """任务管理器"""
    
    @classmethod
    def init(cls):
        """初始化"""
        ensure_dirs()
        os.makedirs(TASK_LOG_DIR, exist_ok=True)
        if not os.path.exists(TASK_FILE):
            cls._save_tasks([])
    
    @classmethod
    def _load_tasks(cls) -> List[dict]:
        """加载任务"""
        if not os.path.exists(TASK_FILE):
            return []
        try:
            with open(TASK_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    
    @classmethod
    def _save_tasks(cls, tasks: List[dict]):
        """保存任务"""
        with open(TASK_FILE, 'w') as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def add(cls, task_type: str, command: str, interval: int = 0, schedule: str = ""):
        """添加任务"""
        cls.init()
        tasks = cls._load_tasks()
        
        task_id = datetime.now().strftime("%Y%m%d%H%M%S")
        task = {
            "id": task_id,
            "type": task_type,  # once, interval, schedule
            "command": command,
            "interval": interval,
            "schedule": schedule,
            "status": "pending",
            "created": datetime.now().isoformat(),
            "last_run": "",
            "next_run": ""
        }
        
        # 计算下次运行时间
        if task_type == "interval" and interval > 0:
            task["next_run"] = datetime.now().isoformat()
        elif task_type == "schedule":
            task["next_run"] = cls._calc_next_run(schedule)
        
        tasks.append(task)
        cls._save_tasks(tasks)
        UI.success(f"任务 {task_id} 已添加")
        return task_id
    
    @classmethod
    def _calc_next_run(cls, schedule: str) -> str:
        """计算下次运行时间（简化版）"""
        # 简化处理，实际应解析cron表达式
        return datetime.now().isoformat()
    
    @classmethod
    def delete(cls, task_id: str):
        """删除任务"""
        tasks = cls._load_tasks()
        new_tasks = [t for t in tasks if t["id"] != task_id]
        
        if len(new_tasks) == len(tasks):
            UI.error(f"任务 {task_id} 不存在")
            return
        
        cls._save_tasks(new_tasks)
        UI.success(f"任务 {task_id} 已删除")
    
    @classmethod
    def list(cls) -> List[dict]:
        """列出任务"""
        return cls._load_tasks()
    
    @classmethod
    def show_list(cls):
        """显示任务列表"""
        UI.section("任务列表")
        tasks = cls.list()
        
        if not tasks:
            UI.warn("暂无任务")
            return
        
        for t in tasks:
            status_color = {
                "pending": UI.YELLOW,
                "running": UI.GREEN,
                "completed": UI.DIM,
                "failed": UI.RED
            }.get(t["status"], "")
            
            type_str = {
                "once": "一次性",
                "interval": "周期",
                "schedule": "定时"
            }.get(t["type"], t["type"])
            
            print(f" {status_color}●{UI.END} {t['id']} [{type_str}]")
            print(f"   命令: {t['command']}")
            if t['type'] == 'interval':
                print(f"   间隔: {t['interval']}秒")
            print(f"   状态: {t['status']}")
            print()
    
    @classmethod
    def start_daemon(cls):
        """启动任务守护进程"""
        # 检查是否已在运行
        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE, 'r') as f:
                    pid = int(f.read().strip())
                os.kill(pid, 0)  # 检查进程是否存在
                UI.warn("任务守护进程已在运行")
                return
            except:
                pass
        
        # 启动守护进程
        daemon_script = f'''
import sys
sys.path.insert(0, "{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}")
import time
import os
import json
import subprocess
from datetime import datetime

TASK_FILE = "{TASK_FILE}"
PID_FILE = "{PID_FILE}"
TASK_LOG_DIR = "{TASK_LOG_DIR}"

# 写入PID
with open(PID_FILE, 'w') as f:
    f.write(str(os.getpid()))

def run_task(task):
    log_file = os.path.join(TASK_LOG_DIR, f"{{task['id']}}.log")
    with open(log_file, 'a') as f:
        f.write(f"{{datetime.now().isoformat()}} - 执行: {{task['command']}}\\n")
    try:
        result = subprocess.run(task['command'], shell=True, capture_output=True, text=True, timeout=300)
        with open(log_file, 'a') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write(f"ERROR: {{result.stderr}}\\n")
    except Exception as e:
        with open(log_file, 'a') as f:
            f.write(f"ERROR: {{e}}\\n")

while True:
    try:
        if os.path.exists(TASK_FILE):
            with open(TASK_FILE, 'r') as f:
                tasks = json.load(f)
            now = datetime.now()
            updated = False
            for task in tasks:
                if task['status'] == 'pending':
                    if task['type'] == 'once':
                        run_task(task)
                        task['status'] = 'completed'
                        updated = True
                    elif task['type'] == 'interval':
                        last = datetime.fromisoformat(task['last_run']) if task['last_run'] else datetime.min
                        if (now - last).total_seconds() >= task['interval']:
                            run_task(task)
                            task['last_run'] = now.isoformat()
                            updated = True
            if updated:
                with open(TASK_FILE, 'w') as f:
                    json.dump(tasks, f, indent=2)
    except:
        pass
    time.sleep(10)
'''
        # 在后台运行
        import sys
        python_path = sys.executable
        subprocess.Popen([python_path, "-c", daemon_script], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        UI.success("任务守护进程已启动")
    
    @classmethod
    def stop_daemon(cls):
        """停止任务守护进程"""
        if not os.path.exists(PID_FILE):
            UI.warn("任务守护进程未运行")
            return
        
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            os.remove(PID_FILE)
            UI.success("任务守护进程已停止")
        except Exception as e:
            UI.error(f"停止失败: {e}")
    
    @classmethod
    def run_now(cls, task_id: str):
        """立即执行任务"""
        tasks = cls._load_tasks()
        task = next((t for t in tasks if t["id"] == task_id), None)
        
        if not task:
            UI.error(f"任务 {task_id} 不存在")
            return
        
        UI.info(f"执行任务: {task['command']}")
        try:
            result = subprocess.run(task["command"], shell=True, capture_output=True, text=True, timeout=300)
            print(result.stdout)
            if result.stderr:
                print(f"Error: {result.stderr}")
            
            # 更新任务状态
            task["last_run"] = datetime.now().isoformat()
            cls._save_tasks(tasks)
            UI.success("任务执行完成")
        except Exception as e:
            UI.error(f"执行失败: {e}")


def handle_task_command(args: List[str]):
    """处理任务命令"""
    if not args:
        TaskManager.show_list()
        return
    
    cmd = args[0]
    
    if cmd == "add":
        if len(args) < 3:
            print("用法: ai task add <类型> <命令> [间隔/时间]")
            print("类型: once(一次性), interval(周期), schedule(定时)")
            return
        task_type = args[1]
        command = args[2]
        extra = args[3] if len(args) > 3 else ""
        
        interval = int(extra) if extra.isdigit() else 0
        TaskManager.add(task_type, command, interval)
    
    elif cmd == "del":
        if len(args) < 2:
            UI.error("请指定任务ID")
            return
        TaskManager.delete(args[1])
    
    elif cmd == "run":
        if len(args) < 2:
            UI.error("请指定任务ID")
            return
        TaskManager.run_now(args[1])
    
    elif cmd == "start":
        TaskManager.start_daemon()
    
    elif cmd == "stop":
        TaskManager.stop_daemon()
    
    elif cmd == "list":
        TaskManager.show_list()
    
    else:
        print("用法: ai task <add|del|run|start|stop|list>")
