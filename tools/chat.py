"""
AI CLI 对话功能
"""

import os
import sys
import json
import re
import readline
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from .constants import HISTORY_DIR, ensure_dirs
from .config_mgr import ConfigManager
from .plugin import PluginManager, MCPToolManager
from .ui import UI
from .core.input_handler import InputHandler


class ChatEngine:
    """对话引擎"""
    
    def __init__(self):
        self.input_handler = InputHandler("", allow_multiline=True)
    
    @classmethod
    async def ask(cls, question: str, stream: bool = True) -> str:
        """即时问答"""
        client, model = ConfigManager.get_client()
        if not client:
            UI.error("未配置供应商，使用 'ai new <名称>' 创建")
            return ""
        
        # 获取MCP工具
        mgr = MCPToolManager()
        await mgr.initialize()
        tools = await mgr.get_tools()
        
        # 添加进化工具
        tools.extend(cls._get_evolution_tools())
        
        messages = [
            {"role": "system", "content": cls._get_system_prompt()},
            {"role": "user", "content": question}
        ]
        
        return await cls._chat_loop(client, model, messages, tools, mgr, stream)
    
    @classmethod
    async def chat_session(cls, session_file: str = None, messages: list = None):
        """对话会话"""
        client, model = ConfigManager.get_client()
        if not client:
            UI.error("未配置供应商，使用 'ai new <名称>' 创建")
            return
        
        ensure_dirs()
        if not session_file:
            session_file = os.path.join(HISTORY_DIR, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        # 获取MCP工具
        mgr = MCPToolManager()
        await mgr.initialize()
        tools = await mgr.get_tools()
        tools.extend(cls._get_evolution_tools())
        
        # 初始化消息
        if messages:
            msg_list = messages
        else:
            msg_list = [{"role": "system", "content": cls._get_system_prompt()}]
        
        UI.section("对话模式")
        print("多行输入支持:")
        print("  - 以 \\ 结尾继续输入下一行")
        print("  - 输入 ``` 开始多行块，再输入 ``` 结束")
        print()
        print("输入 'exit' 退出, 'clear' 清空上下文\n")
        
        # 创建输入处理器
        input_handler = InputHandler("", allow_multiline=True)
        
        while True:
            try:
                print("You > ", end="", flush=True)
                user_input = input_handler.get_input()
                
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit"]:
                    break
                if user_input.lower() == "clear":
                    msg_list = [msg_list[0]]  # 保留system
                    UI.success("已清空上下文")
                    continue
                
                msg_list.append({"role": "user", "content": user_input})
                print(f"{UI.CYAN}AI > {UI.END}", end="", flush=True)
                
                response = await cls._chat_loop(client, model, msg_list, tools, mgr, stream=True)
                msg_list.append({"role": "assistant", "content": response})
                
                # 保存会话
                cls._save_session(session_file, msg_list)
                
            except KeyboardInterrupt:
                break
    
    @classmethod
    async def _chat_loop(cls, client, model, messages, tools, mgr, stream=True) -> str:
        """对话循环"""
        full_response = ""
        
        while True:
            try:
                res = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools if tools else None,
                    stream=stream
                )
                
                if stream:
                    full_response, tool_calls = await cls._handle_stream(res)
                else:
                    full_response = res.choices[0].message.content or ""
                    tool_calls = res.choices[0].message.tool_calls or []
                
                if not tool_calls:
                    if stream:
                        print()
                    return full_response
                
                # 处理工具调用
                messages.append({
                    "role": "assistant",
                    "content": full_response or None,
                    "tool_calls": tool_calls
                })
                
                for tc in tool_calls:
                    result = await cls._handle_tool_call(tc, mgr, tools)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": tc["function"]["name"],
                        "content": result
                    })
                    
            except Exception as e:
                UI.error(f"对话出错: {e}")
                return full_response
    
    @classmethod
    def _clean_stream_output(cls, content: str) -> str:
        """清理流式输出中的异常 token"""
        if not content:
            return content
        
        # 移除常见的异常 token 标记
        patterns = [
            r'<\|tool_calls_section_begin\|>',
            r'<\|tool_calls_section_end\|>',
            r'<\|tool_call_begin\|>',
            r'<\|tool_call_end\|>',
            r'<\|tool_call_argument_begin\|>',
            r'<\|tool_call_argument_end\|>',
            r'<\|tool_call_argument\|>',
            r'<\|.*?\|>',  # 其他类似的标记
        ]
        
        cleaned = content
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned)
        
        # 移除 "functions.xxx:n" 这样的残留片段
        cleaned = re.sub(r'functions\.\w+:\d+\s*', '', cleaned)
        
        # 移除孤立的 JSON 对象片段
        cleaned = re.sub(r'\{\s*"[^"]+"\s*:\s*"[^"]*"[^}]*\}\s*', '', cleaned)
        
        # 移除多余的空白
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    @classmethod
    async def _handle_stream(cls, response) -> tuple:
        """处理流式响应"""
        full = ""
        tool_calls = []
        
        for chunk in response:
            if not chunk.choices:
                continue
            
            delta = chunk.choices[0].delta
            
            if delta.content:
                raw_content = delta.content
                # 清理异常标记后再输出
                clean_content = cls._clean_stream_output(raw_content)
                if clean_content:
                    print(clean_content, end="", flush=True)
                full += raw_content
            
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    while len(tool_calls) <= tc.index:
                        tool_calls.append({
                            "id": f"c_{tc.index}",
                            "type": "function",
                            "function": {"name": "", "arguments": ""}
                        })
                    target = tool_calls[tc.index]
                    if tc.id:
                        target["id"] = tc.id
                    if tc.function.name:
                        target["function"]["name"] += tc.function.name
                    if tc.function.arguments:
                        target["function"]["arguments"] += tc.function.arguments
        
        # 清理完整输出
        full = cls._clean_stream_output(full)
        
        return full, tool_calls
    
    @classmethod
    async def _handle_tool_call(cls, tc: dict, mgr: MCPToolManager, tools: list) -> str:
        """处理工具调用"""
        name = tc["function"]["name"]
        try:
            args = json.loads(tc["function"]["arguments"])
        except:
            args = {}
        
        UI.info(f"调用: {name}")
        
        # 进化工具
        if name == "search_plugin":
            results = PluginManager.search(args.get("query", ""))
            return cls._format_search_results(results)
        
        elif name == "install_plugin":
            success = await PluginManager.install(args.get("name", ""))
            if success:
                # 重新加载工具
                await mgr.initialize()
                new_tools = await mgr.get_tools()
                existing = {t["function"]["name"] for t in tools}
                for t in new_tools:
                    if t["function"]["name"] not in existing:
                        tools.append(t)
            return "安装成功" if success else "安装失败"
        
        elif name == "analyze_gap":
            return "分析完成"
        
        # MCP工具
        elif "__" in name:
            return await mgr.call(name, args)
        
        return "未知工具"
    
    @classmethod
    def _get_system_prompt(cls) -> str:
        """获取系统提示"""
        return """你是AI CLI，一个智能助手。

当发现当前工具无法完成任务时：
1. 使用 search_plugin 搜索相关插件
2. 使用 install_plugin 安装插件
3. 安装后可立即使用新工具

你可以自主安装插件，无需确认。"""
    
    @classmethod
    def _get_evolution_tools(cls) -> List[dict]:
        """获取进化工具定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_plugin",
                    "description": "搜索MCP插件",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索关键词"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "install_plugin",
                    "description": "安装MCP插件",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "插件名称"}
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_gap",
                    "description": "分析能力差距",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task": {"type": "string", "description": "任务描述"}
                        }
                    }
                }
            }
        ]
    
    @classmethod
    def _format_search_results(cls, results: list) -> str:
        """格式化搜索结果"""
        if not results:
            return "未找到匹配插件"
        
        lines = ["找到以下插件：\n"]
        for p in results[:10]:
            lines.append(f"- {p.name}: {p.description}")
            if p.required_env:
                lines.append(f"  需要环境变量: {', '.join(p.required_env)}")
        
        return "\n".join(lines)
    
    @classmethod
    def _save_session(cls, filepath: str, messages: list):
        """保存会话"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 提取标题
        title = "新会话"
        for m in messages:
            if m["role"] == "user":
                title = m["content"][:50]
                break
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({"title": title, "messages": messages}, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def list_sessions(cls):
        """列出历史会话"""
        UI.section("历史会话")
        
        if not os.path.exists(HISTORY_DIR):
            os.makedirs(HISTORY_DIR, exist_ok=True)
            UI.warn("暂无历史记录")
            return []
        
        files = sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")], reverse=True)
        
        if not files:
            UI.warn("暂无历史记录")
            return []
        
        sessions = []
        for i, f in enumerate(files[:20], 1):
            try:
                with open(os.path.join(HISTORY_DIR, f), 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    title = data.get("title", "无标题")
                    date_str = f[:8] if len(f) >= 8 else ""
                    UI.item(f"{i}.", f"[{date_str}] {title}")
                    sessions.append((f, data))
            except:
                pass
        
        if sessions:
            print()
            print(f"  {UI.DIM}ai history load <编号>  加载对话")
            print(f"  ai history del <编号>   删除记录{UI.END}")
        
        return sessions
    
    @classmethod
    def load_session(cls, index: int) -> Optional[dict]:
        """加载会话"""
        sessions = []
        if os.path.exists(HISTORY_DIR):
            files = sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")], reverse=True)
            for f in files[:20]:
                try:
                    with open(os.path.join(HISTORY_DIR, f), 'r', encoding='utf-8') as file:
                        sessions.append((f, json.load(file)))
                except:
                    pass
        
        if 0 <= index < len(sessions):
            return sessions[index][1]
        
        UI.error("编号无效")
        return None
    
    @classmethod
    def delete_session(cls, index: int):
        """删除会话"""
        if not os.path.exists(HISTORY_DIR):
            UI.warn("暂无历史记录")
            return
        
        files = sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")], reverse=True)
        
        if 0 <= index < len(files):
            filepath = os.path.join(HISTORY_DIR, files[index])
            os.remove(filepath)
            UI.success("记录已删除")
        else:
            UI.error("编号无效")
