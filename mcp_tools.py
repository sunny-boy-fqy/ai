#!/usr/bin/env python3
import json
import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPToolManager:
    def __init__(self, config_path):
        self.config_path = config_path
        self.server_params = {}

    def load_config(self):
        if not os.path.exists(self.config_path):
            return {"servers": {}}
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except Exception:
            return {"servers": {}}

    async def initialize_tools(self, allowed_paths=None, extra_servers=None):
        config = self.load_config()
        
        # Merge extra servers if provided (e.g. dynamic runtime servers)
        if extra_servers:
            config.setdefault("servers", {}).update(extra_servers)

        for name, cfg in config.get("servers", {}).items():
            command = cfg["command"]
            args = cfg.get("args", [])
            
            # Windows compatibility for npx and other commands
            if sys.platform.startswith("win"):
                if command == "npx":
                    command = "npx.cmd"
                elif command == "npm":
                    command = "npm.cmd"
            
            # Special handling for npx to suppress install messages
            if "npx" in command:
                if "-y" not in args:
                    args.insert(0, "-y")
            
            # Dynamic Override for filesystem paths
            if name == "filesystem" and allowed_paths:
                # The filesystem server usually takes allowed paths as args
                # We need to find where to put them or replace existing ones.
                # Assuming the last args are paths or we append them.
                # Standard mcp-filesystem server usage: npx ... [allowed_paths...]
                # We'll just append the new allowed path if it's not already there
                # Or better, replace all path args with the specific workspace.
                
                # Check if args already have paths (strings not starting with -)
                # This is tricky without knowing exact server impl, but for 
                # @modelcontextprotocol/server-filesystem, args are paths.
                
                # Filter out existing paths to enforce the new workspace strictness if desired,
                # or just append. The user wants "run only in specified working directory".
                # So we should probably clear old paths and set the new one.
                new_args = [a for a in args if a.startswith("-") or a.startswith("@")]
                new_args.extend(allowed_paths)
                args = new_args

            params = StdioServerParameters(
                command=command,
                args=args,
                env=os.environ.copy()
            )
            self.server_params[name] = params

    async def get_tool_definitions(self):
        all_tools = []
        # Suppress stderr during tool discovery to hide "Secure MCP Filesystem Server running on stdio" etc.
        # We redirect stderr to devnull temporarily if possible, but stdio_client might need it.
        # Actually, let's just try to be quiet.
        
        for server_name, params in self.server_params.items():
            try:
                # We use a custom stderr to avoid cluttering the terminal
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        for tool in tools.tools:
                            tool_def = {
                                "type": "function",
                                "function": {
                                    "name": f"{server_name}__{tool.name}",
                                    "description": tool.description,
                                    "parameters": tool.inputSchema
                                }
                            }
                            all_tools.append(tool_def)
            except Exception:
                # Silently fail for individual servers during discovery
                pass
        return all_tools

    async def call_tool(self, full_tool_name, arguments):
        if "__" not in full_tool_name:
            return f"Error: Invalid tool name format {full_tool_name}"
        
        server_name, tool_name = full_tool_name.split("__", 1)
        
        if server_name not in self.server_params:
            return f"Error: Server {server_name} not configured."
        
        try:
            async with stdio_client(self.server_params[server_name]) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    return result.content
        except Exception as e:
            return f"Error calling tool {full_tool_name}: {str(e)}"
