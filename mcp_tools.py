#!/usr/bin/env python3
import json, asyncio, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPToolManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.server_params = {}

    def load_config(self):
        if not os.path.exists(self.config_path): return {"servers": {}}
        try:
            with open(self.config_path, "r", encoding='utf-8') as f: return json.load(f)
        except: return {"servers": {}}

    async def initialize_tools(self, allowed_paths=None, extra_servers=None):
        self.server_params = {}
        config = self.load_config()
        if extra_servers: config.setdefault("servers", {}).update(extra_servers)
        for name, cfg in config.get("servers", {}).items():
            command = cfg["command"]
            args = cfg.get("args", [])
            if sys.platform.startswith("win"):
                if command == "npx": command = "npx.cmd"
                elif command == "npm": command = "npm.cmd"
            if "npx" in command and "-y" not in args: args.insert(0, "-y")
            if name == "filesystem" and allowed_paths:
                new_args = [a for a in args if a.startswith("-") or a.startswith("@")]
                new_args.extend(allowed_paths)
                args = new_args
            # 严格隔离环境
            self.server_params[name] = StdioServerParameters(command=command, args=args, env=os.environ.copy())

    async def get_tool_definitions(self):
        all_tools = []
        for server_name, params in self.server_params.items():
            try:
                # 增加 10 秒超时防止卡死
                async with asyncio.timeout(10.0):
                    async with stdio_client(params) as (read, write):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            tools = await session.list_tools()
                            for tool in tools.tools:
                                all_tools.append({
                                    "type": "function",
                                    "function": {
                                        "name": f"{server_name}__{tool.name}",
                                        "description": tool.description,
                                        "parameters": tool.inputSchema
                                    }
                                })
            except: pass
        return all_tools

    async def call_tool(self, full_name, arguments):
        if "__" not in full_name: return f"Error: Invalid format {full_name}"
        srv, t_name = full_name.split("__", 1)
        if srv not in self.server_params: return f"Error: Server {srv} not found"
        try:
            async with asyncio.timeout(30.0):
                async with stdio_client(self.server_params[srv]) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        res = await session.call_tool(t_name, arguments)
                        return res.content
        except Exception as e: return f"Error: {e}"
