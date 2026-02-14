"""
AI CLI 工作目录管理
用于 ai init 和 ai work 命令
"""

import os
from .constants import AI_WORK_DIR_CONFIG, ensure_dirs
from .ui import UI


class WorkspaceManager:
    """工作目录管理器"""
    
    @classmethod
    def get_work_dir(cls) -> str:
        """获取当前工作目录"""
        ensure_dirs()
        if os.path.exists(AI_WORK_DIR_CONFIG):
            try:
                with open(AI_WORK_DIR_CONFIG, 'r', encoding='utf-8') as f:
                    path = f.read().strip()
                    if path and os.path.isdir(path):
                        return path
            except:
                pass
        return ""
    
    @classmethod
    def set_work_dir(cls, path: str):
        """设置工作目录"""
        ensure_dirs()
        abs_path = os.path.abspath(path)
        if not os.path.isdir(abs_path):
            try:
                os.makedirs(abs_path, exist_ok=True)
            except Exception as e:
                UI.error(f"无法创建目录: {e}")
                return
        
        with open(AI_WORK_DIR_CONFIG, 'w', encoding='utf-8') as f:
            f.write(abs_path)
        
        # 同时添加到 MCP workspace 配置
        cls._add_to_mcp_workspaces(abs_path)
    
    @classmethod
    def _add_to_mcp_workspaces(cls, path: str):
        """将路径添加到 MCP workspace 配置"""
        from .constants import WORKSPACE_CONFIG
        ensure_dirs()
        
        # 读取现有工作区
        workspaces = []
        if os.path.exists(WORKSPACE_CONFIG):
            try:
                with open(WORKSPACE_CONFIG, 'r', encoding='utf-8') as f:
                    workspaces = [line.strip() for line in f if line.strip()]
            except:
                pass
        
        # 如果路径不在列表中，添加它
        if path not in workspaces:
            workspaces.append(path)
            with open(WORKSPACE_CONFIG, 'w', encoding='utf-8') as f:
                f.write('\n'.join(workspaces))
            
            # 更新 MCP filesystem 配置
            cls._update_filesystem_config(workspaces)
    
    @classmethod
    def _update_filesystem_config(cls, paths: list):
        """更新 MCP filesystem 插件配置"""
        import json
        from .constants import MCP_DIR, MCP_CONFIG_FILE
        
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
        
        UI.info(f"已更新 MCP filesystem 配置")
    
    @classmethod
    def check_and_prompt(cls) -> bool:
        """检查工作目录配置，未配置时提示用户"""
        if cls.get_work_dir():
            return True
        
        UI.section("工作目录配置")
        UI.warn("尚未设置工作目录")
        print(f"\n  请先运行 'ai init' 初始化工作目录")
        print(f"  或导航到目标文件夹后运行 'ai init'\n")
        return False
    
    @classmethod
    def handle_command(cls, args):
        """处理 workspace 命令（兼容旧接口）"""
        from .set_workspace import WorkspaceManager as OldWM
        OldWM.handle_command(args)
