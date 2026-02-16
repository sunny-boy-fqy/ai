#!/usr/bin/env python3
"""
AI CLI - 智能命令行助手
"""
import readline
import sys
import asyncio
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.config_mgr import ConfigManager
from tools.provider import ProviderManager
from tools.plugin import PluginManager
from tools.task import TaskManager, handle_task_command
from tools.sync import SyncManager, UpdateManager
from tools.chat import ChatEngine
from tools.set_workspace import WorkspaceManager
from tools.ui import UI

# 导入日志模块
from tools.logger import set_log_level, DEBUG, INFO

# 导入 Leader-Worker 模块
from tools.core.init import AIInitializer
from tools.core.leader_worker import LeaderAI, run_leader_worker_session


def handle_history(args):
    """处理历史命令"""
    if not args:
        ChatEngine.list_sessions()
        return

    sub = args[0]

    if sub == "load":
        if len(args) < 2:
            UI.error("请输入编号")
            return
        try:
            idx = int(args[1]) - 1
            data = ChatEngine.load_session(idx)
            if data:
                asyncio.run(ChatEngine.chat_session(messages=data.get("messages", [])))
        except ValueError:
            UI.error("编号无效")

    elif sub == "del":
        if len(args) < 2:
            UI.error("请输入编号")
            return
        try:
            idx = int(args[1]) - 1
            ChatEngine.delete_session(idx)
        except ValueError:
            UI.error("编号无效")

    else:
        ChatEngine.list_sessions()


def handle_delete(args):
    """处理删除命令"""
    if not args:
        UI.error("用法: ai del <provider|plugin|task|history|workspace> <名称>")
        return

    target = args[0].lower()

    if target == "provider":
        ProviderManager.delete(args[1] if len(args) > 1 else None)

    elif target == "plugin":
        PluginManager.uninstall(args[1] if len(args) > 1 else None)

    elif target == "task":
        if len(args) < 2:
            UI.error("请输入任务ID")
            return
        TaskManager.delete(args[1])

    elif target == "history":
        if len(args) < 2:
            UI.error("请输入编号")
            return
        try:
            idx = int(args[1]) - 1
            ChatEngine.delete_session(idx)
        except ValueError:
            UI.error("编号无效")

    elif target == "workspace":
        # 删除工作区
        WorkspaceManager.handle_command(["rm"] + args[1:])

    else:
        # 默认当作供应商
        ProviderManager.delete(target)


def handle_workspace(args):
    """处理工作区命令"""
    WorkspaceManager.handle_command(args)


def handle_init(args):
    """处理初始化命令"""
    # 获取当前目录
    current_dir = os.getcwd()
    
    initializer = AIInitializer(current_dir)
    
    if initializer.is_initialized():
        UI.warn(f"当前目录已初始化: {initializer.ai_dir}")
        if UI.confirm("是否重新初始化？"):
            import shutil
            shutil.rmtree(initializer.ai_dir)
        else:
            initializer.show_status()
            return
    
    # 检查参数
    auto_mode = "--auto" in args or "-a" in args
    
    if auto_mode:
        # 自动模式：使用全局配置
        success = initializer.auto_initialize()
    else:
        # 交互模式：让用户选择
        success = initializer.initialize()
    
    if success:
        print()
        UI.success("初始化完成！现在可以使用 'ai work' 进入工作模式")


async def handle_work(args):
    """处理 work 命令 - 启动 Leader-Worker 会话"""
    # 解析参数
    debug_mode = "--debug" in args or "-d" in args
    resume_mode = "--resume" in args or "-r" in args
    
    # 过滤掉参数标志
    args = [a for a in args if a not in ["--debug", "-d", "--resume", "-r"]]
    
    # 设置日志级别
    if debug_mode:
        set_log_level(DEBUG)
        UI.info("调试模式已启用")
    
    # 获取当前目录
    current_dir = os.getcwd()
    
    initializer = AIInitializer(current_dir)
    
    # 检查是否已初始化
    if not initializer.is_initialized():
        UI.info("当前目录未初始化，正在自动初始化...")
        
        # 自动初始化
        if not initializer.auto_initialize():
            UI.error("初始化失败，请手动运行 'ai init'")
            return
    
    # 启动 Leader-Worker 会话
    ai_dir = initializer.ai_dir
    
    leader = LeaderAI(ai_dir)
    
    if not leader.is_ready():
        UI.error("Leader AI 配置不完整，请运行 'ai init' 重新配置")
        return
    
    # 检查是否需要恢复任务
    if resume_mode:
        pending_tasks = leader.task_manager.get_tasks_by_status("in_progress")
        pending_tasks.extend(leader.task_manager.get_tasks_by_status("pending"))
        
        if pending_tasks:
            UI.section(f"发现 {len(pending_tasks)} 个未完成的任务")
            leader.task_manager.show_progress()
            
            if UI.confirm("是否继续执行这些任务？", default=True):
                # 将第一个进行中的任务状态重置为待处理
                for task in pending_tasks:
                    if task.get("status") == "in_progress":
                        leader.task_manager.set_task_status(task["id"], "pending")
                
                UI.info("任务状态已恢复，继续执行...")
            else:
                UI.info("已取消任务恢复")
                return
        else:
            UI.info("没有未完成的任务")
            return
    
    # 检查是否有任务文件参数
    if args and args[0] == "--file":
        if len(args) < 2:
            UI.error("请指定任务文件路径")
            return
        
        # 从文件读取任务
        task_file = args[1]
        if not os.path.exists(task_file):
            UI.error(f"任务文件不存在: {task_file}")
            return
        
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                task_content = f.read()
            
            UI.info(f"读取任务文件: {task_file}")
            UI.section("任务内容")
            print(task_content[:500] + "..." if len(task_content) > 500 else task_content)
            print()
            
            # 一次性执行任务
            await run_single_task(leader, task_content)
            return
        except Exception as e:
            UI.error(f"读取任务文件失败: {e}")
            return
    
    # 检查是否有内联任务参数
    if args and args[0] == "--task":
        if len(args) < 2:
            UI.error("请提供任务描述")
            return
        
        task_content = " ".join(args[1:])
        UI.info("执行任务: " + task_content[:100] + "..." )
        await run_single_task(leader, task_content)
        return
    
    # 否则进入交互式会话
    await run_leader_worker_session(ai_dir)


async def run_single_task(leader, task_content: str):
    """
    执行单个任务（非交互式）
    
    Args:
        leader: LeaderAI 实例
        task_content: 任务内容
    """
    UI.section("开始执行任务")
    print(f"Leader 模型: {leader.config.get('model')}")
    print(f"Worker 模型: {leader.worker_config.get('model')}")
    print()
    
    try:
        # 静默初始化 MCP（隐藏服务器启动信息）
        import sys
        import os
        from contextlib import contextmanager
        
        @contextmanager
        def suppress_output():
            old_stdout = sys.stdout
            try:
                sys.stdout = open(os.devnull, 'w')
                yield
            finally:
                sys.stdout.close()
                sys.stdout = old_stdout
        
        with suppress_output():
            await leader.mcp_manager.initialize(silent=True)
        
        UI.success(f"MCP 管理器初始化完成，已加载 {len(leader.mcp_manager.server_params)} 个插件")
        
        # 执行任务
        await leader.process_user_input(task_content)
        
        UI.section("任务执行完成")
        leader.task_manager.show_progress()
        
    except KeyboardInterrupt:
        print("\n任务已取消")
    except Exception as e:
        import traceback
        UI.error(f"任务执行失败: {e}")
        print(traceback.format_exc())


def check_workspace() -> bool:
    """检查工作区配置，未配置时提示用户配置"""
    return WorkspaceManager.check_and_prompt()


def main():
    """主入口"""
    args = sys.argv[1:]

    # 无参数显示帮助
    if not args:
        UI.show_help()
        return
    
    # 检查全局 debug 参数
    debug_mode = "--debug" in args or "-d" in args
    if debug_mode:
        args = [a for a in args if a not in ["--debug", "-d"]]
        set_log_level(DEBUG)
        UI.info("调试模式已启用")

    cmd = args[0].lower() if args else ""

    # 初始化配置
    ConfigManager.init()

    # 对话命令
    if cmd == "ask":
        if len(args) < 2:
            UI.error("请输入问题")
            return
        # 强制检查工作区配置
        if not check_workspace():
            return
        question = " ".join(args[1:])
        asyncio.run(ChatEngine.ask(question))

    elif cmd == "chat":
        # 强制检查工作区配置
        if not check_workspace():
            return
        asyncio.run(ChatEngine.chat_session())

    elif cmd == "history":
        handle_history(args[1:])

    # 供应商命令
    elif cmd == "new":
        ProviderManager.create(args[1] if len(args) > 1 else None)

    elif cmd == "use":
        ProviderManager.use(args[1] if len(args) > 1 else None)

    elif cmd == "model":
        ProviderManager.model(args[1] if len(args) > 1 else None)

    elif cmd == "list":
        ProviderManager.show_list()

    elif cmd == "del":
        handle_delete(args[1:])

    # 工作区命令
    elif cmd == "workspace":
        handle_workspace(args[1:])

    # 初始化命令
    elif cmd == "init":
        handle_init(args[1:])

    # Leader-Worker 工作命令
    elif cmd == "work":
        asyncio.run(handle_work(args[1:]))

    # 插件命令
    elif cmd == "search":
        if len(args) < 2:
            UI.error("请输入搜索关键词")
            return
        PluginManager.show_search(" ".join(args[1:]))

    elif cmd == "install":
        if len(args) < 2:
            UI.error("请输入插件名称")
            return
        asyncio.run(PluginManager.install(args[1]))

    elif cmd == "plugin":
        PluginManager.show_installed()

    # 任务命令
    elif cmd == "task":
        handle_task_command(args[1:])

    # 同步命令
    elif cmd == "sync":
        SyncManager.sync_from_remote(args[1] if len(args) > 1 else None)

    elif cmd == "update":
        if len(args) > 1:
            SyncManager.sync_to_remote(args[1])
        else:
            UpdateManager.update_self()

    # 状态命令
    elif cmd == "status":
        # 检查是否在已初始化的目录
        current_dir = os.getcwd()
        initializer = AIInitializer(current_dir)
        
        if initializer.is_initialized():
            initializer.show_status()
        else:
            ProviderManager.show_status()

    elif cmd == "version":
        UpdateManager.show_version()

    # 帮助
    elif cmd in ["-h", "--help", "help"]:
        UI.show_help()

    else:
        # 未知命令当作问题（也需要检查工作区）
        if not check_workspace():
            return
        asyncio.run(ChatEngine.ask(" ".join(args)))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
    except Exception as e:
        UI.error(f"错误: {e}")
