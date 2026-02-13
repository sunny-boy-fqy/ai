"""
AI CLI MCP插件管理
"""

import os
import sys
import json
import asyncio
import subprocess
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from .constants import (
    MCP_DIR, MCP_CONFIG_FILE, PLUGIN_CACHE_FILE,
    BUILTIN_PLUGINS, CAPABILITY_KEYWORDS,
    IS_WINDOWS, get_npx_path
)
from .ui import UI


@dataclass
class PluginInfo:
    """插件信息"""
    name: str = ""
    npm_package: str = ""
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    install_cmd: str = "npx"
    install_args: List[str] = field(default_factory=list)
    required_env: List[str] = field(default_factory=list)
    verified: bool = False


class PluginManager:
    """插件管理器"""
    
    @classmethod
    def _ensure_config(cls):
        """确保配置文件存在"""
        os.makedirs(MCP_DIR, exist_ok=True)
        if not os.path.exists(MCP_CONFIG_FILE):
            with open(MCP_CONFIG_FILE, 'w') as f:
                json.dump({"servers": {}}, f, indent=2)
    
    @classmethod
    def list_installed(cls) -> Dict[str, dict]:
        """列出已安装插件"""
        cls._ensure_config()
        try:
            with open(MCP_CONFIG_FILE, 'r') as f:
                return json.load(f).get("servers", {})
        except:
            return {}
    
    @classmethod
    def search(cls, query: str = "") -> List[PluginInfo]:
        """搜索插件"""
        results = []
        query_lower = query.lower() if query else ""
        
        # 搜索内置插件
        for name, data in BUILTIN_PLUGINS.items():
            # 匹配名称、描述、能力
            caps = data.get("capabilities", [])
            caps_str = " ".join(caps).lower()
            desc = data.get("description", "").lower()
            
            if not query or query_lower in name.lower() or query_lower in desc or query_lower in caps_str:
                info = PluginInfo()
                for k, v in data.items():
                    setattr(info, k, v)
                results.append(info)
        
        # 搜索网络缓存
        try:
            if os.path.exists(PLUGIN_CACHE_FILE):
                with open(PLUGIN_CACHE_FILE, 'r') as f:
                    cache = json.load(f)
                for name, data in cache.get("plugins", {}).items():
                    caps = data.get("capabilities", [])
                    caps_str = " ".join(caps).lower()
                    desc = data.get("description", "").lower()
                    
                    if not query or query_lower in name.lower() or query_lower in desc or query_lower in caps_str:
                        info = PluginInfo()
                        info.name = name
                        info.description = data.get("description", "")
                        info.install_cmd = data.get("install_cmd", "npx")
                        info.install_args = data.get("install_args", [])
                        info.capabilities = caps
                        results.append(info)
        except:
            pass
        
        return results[:20]
    
    @classmethod
    async def install(cls, name: str) -> bool:
        """安装插件"""
        # 获取插件信息
        if name in BUILTIN_PLUGINS:
            data = BUILTIN_PLUGINS[name]
        else:
            UI.error(f"未知插件 '{name}'，使用 'ai search <关键词>' 搜索")
            return False
        
        # 检查环境变量
        required_env = data.get("required_env", [])
        missing = [e for e in required_env if not os.environ.get(e)]
        if missing:
            UI.error(f"需要环境变量: {', '.join(missing)}")
            UI.info(f"示例: export {missing[0]}='your-value'")
            return False
        
        # 检查是否已安装
        installed = cls.list_installed()
        if name in installed:
            UI.warn(f"插件 '{name}' 已安装")
            return True
        
        # 写入配置
        cmd = data.get("install_cmd", "npx")
        args = data.get("install_args", [])
        
        # 确保npx路径
        if cmd == "npx":
            npx_path = get_npx_path()
            if os.path.exists(npx_path):
                cmd = npx_path
            elif IS_WINDOWS:
                cmd = "npx.cmd"
        
        # 确保 -y 参数
        if "npx" in cmd:
            if "-y" not in args:
                args = ["-y"] + args
        
        cls._ensure_config()
        installed[name] = {
            "command": cmd,
            "args": args
        }
        
        with open(MCP_CONFIG_FILE, 'w') as f:
            json.dump({"servers": installed}, f, indent=2, ensure_ascii=False)
        
        # 验证安装
        UI.info(f"正在安装 {name}...")
        ok, tools = await cls._verify(name, cmd, args)
        
        if ok:
            UI.success(f"插件 '{name}' 安装成功，加载 {len(tools)} 个工具")
            return True
        else:
            UI.warn("安装后验证失败，但配置已保存")
            return True
    
    @classmethod
    async def _verify(cls, name: str, cmd: str, args: List[str]) -> Tuple[bool, List[str]]:
        """验证插件安装"""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            
            # 隐藏 MCP server 的 stderr 输出
            params = StdioServerParameters(
                command=cmd,
                args=args,
                env=os.environ.copy(),
                stderr=subprocess.DEVNULL  # 隐藏服务器输出
            )
            
            async with asyncio.timeout(15.0):
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        return True, [t.name for t in tools.tools]
        except Exception as e:
            return False, []
    
    @classmethod
    def uninstall(cls, name: str = None):
        """卸载插件"""
        installed = cls.list_installed()
        
        if not installed:
            UI.warn("无已安装插件")
            return
        
        if not name:
            print()
            plugins = list(installed.keys())
            for i, p in enumerate(plugins, 1):
                UI.item(f"{i}.", p)
            
            inp = UI.input("选择要卸载的编号")
            if not inp:
                return
            try:
                idx = int(inp) - 1
                if 0 <= idx < len(plugins):
                    name = plugins[idx]
                else:
                    UI.error("编号无效")
                    return
            except:
                UI.error("请输入编号")
                return
        
        if name not in installed:
            UI.error(f"插件 '{name}' 未安装")
            return
        
        if UI.confirm(f"确定卸载 '{name}'？"):
            del installed[name]
            cls._ensure_config()
            with open(MCP_CONFIG_FILE, 'w') as f:
                json.dump({"servers": installed}, f, indent=2, ensure_ascii=False)
            UI.success(f"插件 '{name}' 已卸载")
    
    @classmethod
    def show_installed(cls):
        """显示已安装插件"""
        UI.section("已安装插件")
        installed = cls.list_installed()
        
        if not installed:
            UI.warn("无已安装插件，使用 'ai install <名称>' 安装")
            return
        
        for name, cfg in installed.items():
            args = " ".join(cfg.get("args", []))
            UI.item(name, args)
    
    @classmethod
    def show_search(cls, query: str):
        """显示搜索结果"""
        UI.section(f"搜索: {query}")
        results = cls.search(query)
        
        if not results:
            UI.warn("未找到匹配插件")
            return
        
        for p in results:
            verified = "✓" if p.verified else " "
            caps = f"[{', '.join(p.capabilities[:3])}]" if p.capabilities else ""
            print(f" {verified} {UI.GREEN}{p.name}{UI.END} {caps}")
            print(f"     {p.description}")
            
            if p.required_env:
                print(f"     {UI.DIM}需: {', '.join(p.required_env)}{UI.END}")


# MCP工具管理器（用于调用）
class MCPToolManager:
    """MCP工具管理器"""
    
    def __init__(self):
        self.server_params = {}
    
    async def initialize(self):
        """初始化工具"""
        try:
            from mcp import StdioServerParameters
        except ImportError:
            return
        
        installed = PluginManager.list_installed()
        for name, cfg in installed.items():
            cmd = cfg.get("command", "npx")
            args = cfg.get("args", [])
            
            if IS_WINDOWS and "npx" in cmd:
                cmd = cmd.replace("npx", "npx.cmd")
            
            try:
                # 隐藏 MCP server 的 stderr 输出
                self.server_params[name] = StdioServerParameters(
                    command=cmd,
                    args=args,
                    env=os.environ.copy(),
                    stderr=subprocess.DEVNULL  # 隐藏服务器输出
                )
            except:
                pass
    
    async def get_tools(self) -> List[dict]:
        """获取所有工具定义"""
        try:
            from mcp import ClientSession
            from mcp.client.stdio import stdio_client
        except ImportError:
            return []
        
        tools = []
        for name, params in self.server_params.items():
            try:
                async with asyncio.timeout(10.0):
                    async with stdio_client(params) as (read, write):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            result = await session.list_tools()
                            for t in result.tools:
                                tools.append({
                                    "type": "function",
                                    "function": {
                                        "name": f"{name}__{t.name}",
                                        "description": t.description,
                                        "parameters": t.inputSchema
                                    }
                                })
            except:
                pass
        return tools
    
    async def call(self, full_name: str, args: dict) -> str:
        """调用工具"""
        try:
            from mcp import ClientSession
            from mcp.client.stdio import stdio_client
        except ImportError:
            return "MCP模块未安装"
        
        if "__" not in full_name:
            return f"无效工具名: {full_name}"
        
        server, tool_name = full_name.split("__", 1)
        if server not in self.server_params:
            return f"未找到服务器: {server}"
        
        try:
            async with asyncio.timeout(30.0):
                async with stdio_client(self.server_params[server]) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(tool_name, args)
                        return str(result.content)
        except Exception as e:
            return f"调用失败: {e}"
