"""
AI CLI 工作区管理
管理 MCP filesystem 插件允许访问的目录
"""

import os
import json
from typing import List, Optional
from .constants import CONFIG_DIR, MCP_DIR, MCP_CONFIG_FILE, ensure_dirs
from .ui import UI


# 工作区配置文件路径
WORKSPACE_CONFIG = os.path.join(CONFIG_DIR, "workspace.config")


class WorkspaceManager:
    """工作区管理器"""

    @classmethod
    def _ensure_config_dir(cls):
        """确保配置目录存在"""
        ensure_dirs()

    @classmethod
    def get_workspaces(cls) -> List[str]:
        """获取工作区列表"""
        if not os.path.exists(WORKSPACE_CONFIG):
            return []
        try:
            with open(WORKSPACE_CONFIG, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            if not content:
                return []
            return [line.strip() for line in content.split('\n') if line.strip()]
        except:
            return []

    @classmethod
    def set_workspaces(cls, paths: List[str]) -> bool:
        """设置工作区列表"""
        # 验证路径
        valid_paths = []
        for path in paths:
            # 展开波浪号
            expanded = os.path.expanduser(path)
            # 转换为绝对路径
            abs_path = os.path.abspath(expanded)
            if os.path.isdir(abs_path):
                valid_paths.append(abs_path)
            else:
                # 尝试创建目录
                try:
                    os.makedirs(abs_path, exist_ok=True)
                    valid_paths.append(abs_path)
                    UI.info(f"已创建目录: {abs_path}")
                except Exception as e:
                    UI.warn(f"无法访问目录 '{path}': {e}")

        if not valid_paths:
            UI.error("没有有效的目录")
            return False

        # 保存工作区配置
        cls._ensure_config_dir()
        with open(WORKSPACE_CONFIG, 'w', encoding='utf-8') as f:
            f.write('\n'.join(valid_paths))

        # 更新 MCP 配置中的 filesystem 插件
        cls._update_filesystem_config(valid_paths)

        return True

    @classmethod
    def add_workspace(cls, path: str) -> bool:
        """添加工作区"""
        expanded = os.path.expanduser(path)
        abs_path = os.path.abspath(expanded)

        # 检查是否已存在
        workspaces = cls.get_workspaces()
        if abs_path in workspaces:
            UI.warn(f"目录 '{abs_path}' 已在工作区列表中")
            return True

        # 验证或创建目录
        if not os.path.isdir(abs_path):
            try:
                os.makedirs(abs_path, exist_ok=True)
                UI.info(f"已创建目录: {abs_path}")
            except Exception as e:
                UI.error(f"无法创建目录 '{path}': {e}")
                return False

        # 添加到列表
        workspaces.append(abs_path)
        cls.set_workspaces(workspaces)
        UI.success(f"已添加工作区: {abs_path}")
        return True

    @classmethod
    def remove_workspace(cls, index: int) -> bool:
        """移除工作区"""
        workspaces = cls.get_workspaces()
        if not (0 <= index < len(workspaces)):
            UI.error("编号无效")
            return False

        removed = workspaces.pop(index)
        cls.set_workspaces(workspaces)
        UI.success(f"已移除工作区: {removed}")
        return True

    @classmethod
    def clear_workspaces(cls):
        """清空工作区"""
        if os.path.exists(WORKSPACE_CONFIG):
            os.remove(WORKSPACE_CONFIG)
        UI.success("已清空工作区配置")

    @classmethod
    def show_workspaces(cls):
        """显示工作区列表"""
        UI.section("工作区配置")
        workspaces = cls.get_workspaces()

        if not workspaces:
            UI.warn("未配置工作区")
            UI.info("使用 'ai workspace <路径>' 添加工作区目录")
            print()
            print(f"  {UI.DIM}工作区是 AI 可以访问的目录范围")
            print(f"  MCP filesystem 插件将只允许访问这些目录{UI.END}")
            return

        print(f"  已配置 {len(workspaces)} 个工作区目录：\n")
        for i, ws in enumerate(workspaces, 1):
            exists = os.path.exists(ws)
            status = f"{UI.GREEN}✓{UI.END}" if exists else f"{UI.RED}✗{UI.END}"
            print(f"  {status} {i}. {ws}")

        print()
        print(f"  {UI.DIM}ai workspace <路径>    添加工作区")
        print(f"  ai workspace rm <编号>  移除工作区")
        print(f"  ai workspace clear      清空工作区{UI.END}")

    @classmethod
    def is_configured(cls) -> bool:
        """检查是否已配置工作区"""
        workspaces = cls.get_workspaces()
        return len(workspaces) > 0

    @classmethod
    def check_and_prompt(cls) -> bool:
        """检查工作区配置，未配置时提示用户"""
        if cls.is_configured():
            return True

        UI.section("工作区配置")
        UI.warn("尚未配置工作区")
        print(f"\n  {UI.CYAN}工作区是 AI 可以访问的目录范围。{UI.END}")
        print(f"  为了安全起见，MCP filesystem 插件只会访问您指定的目录。\n")

        # 提供一些常用选项
        home = os.path.expanduser("~")
        current = os.getcwd()

        print("  快速选择：")
        print(f"  1. 当前目录: {current}")
        print(f"  2. 用户目录: {home}")
        print(f"  3. 自定义路径")
        print()

        choice = UI.input("请选择", "1")

        if choice == "1":
            cls.set_workspaces([current])
        elif choice == "2":
            cls.set_workspaces([home])
        elif choice == "3":
            path = UI.input("请输入目录路径")
            if path:
                cls.set_workspaces([path])
            else:
                UI.error("路径不能为空")
                return False
        else:
            UI.error("无效选择")
            return False

        return cls.is_configured()

    @classmethod
    def _update_filesystem_config(cls, paths: List[str]):
        """更新 MCP filesystem 插件配置"""
        cls._ensure_config_dir()

        # 读取现有配置
        config = {"servers": {}}
        if os.path.exists(MCP_CONFIG_FILE):
            try:
                with open(MCP_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except:
                pass

        # 确保 servers 键存在
        if "servers" not in config:
            config["servers"] = {}

        # 更新 filesystem 配置
        config["servers"]["filesystem"] = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"] + paths
        }

        # 保存配置
        with open(MCP_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        UI.info(f"已更新 MCP filesystem 配置，允许访问 {len(paths)} 个目录")

    @classmethod
    def handle_command(cls, args: List[str]):
        """处理 workspace 命令"""
        if not args:
            cls.show_workspaces()
            return

        sub = args[0].lower()

        if sub in ["rm", "remove", "del", "delete"]:
            if len(args) < 2:
                # 显示列表让用户选择
                workspaces = cls.get_workspaces()
                if not workspaces:
                    UI.warn("无工作区可移除")
                    return
                print()
                for i, ws in enumerate(workspaces, 1):
                    print(f"  {i}. {ws}")
                idx = UI.input("选择要移除的编号")
                if idx.isdigit():
                    cls.remove_workspace(int(idx) - 1)
            else:
                try:
                    idx = int(args[1]) - 1
                    cls.remove_workspace(idx)
                except ValueError:
                    UI.error("请输入有效编号")

        elif sub in ["clear", "reset"]:
            if UI.confirm("确定清空所有工作区配置？"):
                cls.clear_workspaces()

        elif sub in ["set", "="]:
            # 直接设置（覆盖现有配置）
            if len(args) < 2:
                UI.error("请输入目录路径")
                return
            paths = args[1:]
            cls.set_workspaces(paths)

        elif sub in ["add", "+"]:
            # 添加到现有配置
            if len(args) < 2:
                UI.error("请输入目录路径")
                return
            for path in args[1:]:
                cls.add_workspace(path)

        elif sub == "show":
            cls.show_workspaces()

        else:
            # 默认当作路径添加
            for path in args:
                cls.add_workspace(path)