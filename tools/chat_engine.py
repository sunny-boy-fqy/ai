import json, asyncio, sys, os, re
from .constants import CONFIG_DIR, MCP_CONFIG, CONFIG_PATH
from .config_mgr import ConfigManager
from .mcp_mgr import MCPManager
from .session_mgr import SessionManager
from .ui import UI

try: from mcp_tools import MCPToolManager
except: MCPToolManager = None

class ChatEngine:
    @staticmethod
    async def get_client(ctx):
        p = ctx.get("current_provider")
        if not p: return None, None
        sett = ctx.get("provider_settings", {}).get(p, {})
        url = ctx.get("base_urls", {}).get(p)
        p_dir = os.path.join(CONFIG_DIR, p)
        if not os.path.exists(p_dir): return None, None
        keys = sorted([f for f in os.listdir(p_dir) if f.startswith("api")])
        if not keys: return None, None
        kv = open(os.path.join(p_dir, keys[0]), 'r').read().strip()
        try:
            from openai import OpenAI
            return OpenAI(api_key=kv, base_url=url), sett.get("current_model")
        except: return None, None

    @classmethod
    async def chat_completion(cls, client, model, messages, tools, mgr, stream=True, yolo=False, session_file=None):
        while True:
            try:
                res = client.chat.completions.create(model=model, messages=messages, tools=tools or None, stream=stream)
                full, t_calls = "", []
                if stream:
                    for chunk in res:
                        if not hasattr(chunk, 'choices') or not chunk.choices: continue
                        d = chunk.choices[0].delta
                        if d.content: print(d.content, end="", flush=True); full += d.content
                        if d.tool_calls:
                            for tc in d.tool_calls:
                                if len(t_calls) <= tc.index: t_calls.append({"id": f"c_{tc.index}", "type": "function", "function": {"name": "", "arguments": ""}})
                                target = t_calls[tc.index]
                                if tc.id: target["id"] = tc.id
                                if tc.function.name: target["function"]["name"] += tc.function.name
                                if tc.function.arguments: target["function"]["arguments"] += tc.function.arguments
                    print()
                else:
                    m = res.choices[0].message; full = m.content or ""; print(full)
                    if m.tool_calls: t_calls = [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in m.tool_calls]

                if not t_calls: return full
                messages.append({"role": "assistant", "content": full or None, "tool_calls": t_calls})
                for tc in t_calls:
                    name, args_raw = tc["function"]["name"], tc["function"]["arguments"]
                    try: args = json.loads(args_raw)
                    except: args = {}
                    UI.info(f"AI 调用工具: {name}")
                    if name == "install_plugin":
                        await MCPManager.install_plugin(args.get("name"))
                        await mgr.initialize_tools(allowed_paths=[ConfigManager.get_current_workspace()])
                        new_defs = await mgr.get_tool_definitions()
                        for nd in new_defs:
                            if not any(t["function"]["name"] == nd["function"]["name"] for t in tools): tools.append(nd)
                        val = "环境已就绪"
                    elif name == "run_cmd":
                        proc = await asyncio.create_subprocess_shell(args.get("cmd"), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                        o, e = await proc.communicate(); val = f"Out: {o.decode()}\nErr: {e.decode()}"
                    else: val = await mgr.call_tool(name, args)
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "name": name, "content": str(val)})
                if session_file: SessionManager.save_session(session_file, messages)
            except Exception as e: UI.error(f"对话中断: {e}"); return str(e)
