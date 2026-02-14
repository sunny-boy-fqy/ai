#!/usr/bin/env python3
"""
测试调用 mcp-shell-server 插件执行命令
"""
import asyncio
import subprocess
import os
import sys

async def test_mcp_shell_server():
    """测试调用 mcp-shell-server"""
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError:
        print("错误: 未安装 mcp 模块")
        print("请运行: pip install mcp")
        return
    
    # mcp-shell-server 配置
    npx_path = "/home/fangqiyu/.config/ai/node_venv/bin/npx"
    cmd = npx_path
    args = ["-y", "@mkusaka/mcp-shell-server"]
    
    print(f"命令: {' '.join(args)}")
    print("-" * 40)
    
    params = StdioServerParameters(
        command=cmd,
        args=args,
        env=os.environ.copy(),
        stderr=subprocess.DEVNULL
    )
    
    try:
        async with asyncio.timeout(30.0):
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # 列出可用工具
                    tools = await session.list_tools()
                    print(f"可用工具: {[t.name for t in tools.tools]}")
                    print("-" * 40)
                    
                    # 执行一个简单的命令
                    print("执行命令: echo 'Hello from mcp-shell-server!'")
                    result = await session.call_tool("run_command", {
                        "command": "echo 'Hello from mcp-shell-server!'"
                    })
                    print(f"结果: {result.content}")
                    
                    print("-" * 40)
                    
                    # 执行另一个命令 - 查看当前目录
                    print("执行命令: pwd")
                    result = await session.call_tool("run_command", {
                        "command": "pwd"
                    })
                    print(f"结果: {result.content}")
                    
                    print("-" * 40)
                    
                    # 执行 ls 命令
                    print("执行命令: ls -la")
                    result = await session.call_tool("run_command", {
                        "command": "ls -la"
                    })
                    print(f"结果: {result.content}")
                    
    except asyncio.TimeoutError:
        print("错误: 连接超时")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_shell_server())
