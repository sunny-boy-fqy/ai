#!/usr/bin/env python3
"""
AI CLI - 智能命令行助手
"""

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

    cmd = args[0].lower()

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
