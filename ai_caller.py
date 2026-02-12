#!/usr/bin/env python3
import sys, os, asyncio, argparse, json
from datetime import datetime

# 自动处理包导入
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.constants import VERSION_FILE, MCP_CONFIG, SESSION_DIR
from tools.ui import UI
from tools.config_mgr import ConfigManager
from tools.mcp_mgr import MCPManager
from tools.session_mgr import SessionManager
from tools.chat_engine import ChatEngine, MCPToolManager
from tools.sync_mgr import SyncManager
from tools.sys_mgr import SystemManager

# --- 扩展搜索能力 ---
async def search_mcp_market_tool(query=""):
    import httpx
    UI.info(f"正在全网搜索 MCP 插件: {query}...")
    sources = ["https://raw.githubusercontent.com/punkpeye/awesome-mcp/main/README.md", "https://raw.githubusercontent.com/modelcontextprotocol/servers/main/README.md"]
    data = ""
    try:
        async with httpx.AsyncClient() as c:
            for url in sources:
                r = await c.get(url, timeout=5.0)
                if r.status_code == 200: data += r.text + "\n"
        if query:
            lines = [l for l in data.split('\n') if query.lower() in l.lower()]
            return "\n".join(lines[:20]) if lines else "未找到匹配。"
        return data[:3000]
    except: return "搜索失败，请通过网页寻找安装命令。"

async def start_mcp_wrapper(yolo):
    if not MCPToolManager: return None, [], "你是助手。"
    mgr = MCPToolManager(MCP_CONFIG); ws = ConfigManager.get_current_workspace()
    stderr_fd = sys.stderr.fileno()
    with open(os.devnull, 'w') as f:
        old_err = os.dup(stderr_fd)
        try:
            os.dup2(f.fileno(), stderr_fd)
            await mgr.initialize_tools(allowed_paths=[ws])
            tools = await mgr.get_tool_definitions()
        finally: os.dup2(old_err, stderr_fd)
    
    # 注入进化能力
    tools.append({"type":"function", "function":{"name":"search_market", "description":"实时搜索 GitHub 上的数千个 MCP 插件","parameters":{"type":"object","properties":{"query":{"type":"string"}}}}})
    tools.append({"type":"function", "function":{"name":"install_plugin", "description":"通过命令安装任何找到的插件","parameters":{"type":"object","properties":{"name":{"type":"string"},"cmd":{"type":"string"},"args":{"type":"array","items":{"type":"string"}}},"required":["name","cmd","args"]}}})
    if yolo:
        tools.append({"type":"function", "function":{"name":"run_cmd", "description":"执行系统命令","parameters":{"type":"object","properties":{"cmd":{"type":"string"}},"required":["cmd"]}}})
    
    prompt = f"你是 AI CLI。当前工作区: {ws}。能力不足时请先 search_market 找到安装命令，然后 install_plugin。"
    return mgr, tools, prompt

async def start_chat_session(client, model, messages, tools, mgr, yolo, files, session_file=None):
    if not session_file:
        session_file = os.path.join(SESSION_DIR, f"s_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    UI.section("全境对话已就绪")
    if files:
        for f in files:
            if os.path.exists(f):
                content = open(f, 'r', encoding='utf-8', errors='ignore').read()
                messages.append({"role": "user", "content": f"已载入文件 {f}:\n{content}"})
                UI.info(f"附件已挂载: {f}")
    
    while True:
        try:
            line = input("\nYou > ").strip()
            if not line: continue
            if line == '"""':
                print("📝 [进入多行模式] 输入 '\"\"\"' 结束并发送。"); lines = []
                while True:
                    l = input("... "); 
                    if l.strip() == '"""': break
                    lines.append(l)
                inp = "\n".join(lines)
            else: inp = line
            if inp.lower() in ["exit", "quit"]: break
            if inp.lower() == "clear": messages = [messages[0]]; UI.success("上下文已重置。"); continue
            
            messages.append({"role": "user", "content": inp})
            print(f"{UI.CYAN}AI > {UI.END}", end="", flush=True)
            
            # 对话逻辑集成进化能力
            while True:
                res = client.chat.completions.create(model=model, messages=messages, tools=tools or None, stream=True)
                full, t_calls = "", []
                for chunk in res:
                    if not chunk.choices: continue
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
                
                if not t_calls: 
                    messages.append({"role": "assistant", "content": full})
                    break
                
                messages.append({"role": "assistant", "content": full or None, "tool_calls": t_calls})
                for tc in t_calls:
                    name, args_raw = tc["function"]["name"], tc["function"]["arguments"]
                    try: args = json.loads(args_raw)
                    except: args = {}
                    UI.info(f"AI 正在调用能力: {name}...")
                    if name == "search_market": val = await search_mcp_market_tool(args.get("query", ""))
                    elif name == "install_plugin":
                        await MCPManager.install_plugin(args.get("name"), args.get("cmd"), args.get("args", []))
                        stderr_fd = sys.stderr.fileno()
                        with open(os.devnull, 'w') as f:
                            old_err = os.dup(stderr_fd)
                            try:
                                os.dup2(f.fileno(), stderr_fd)
                                await mgr.initialize_tools(allowed_paths=[ConfigManager.get_current_workspace()])
                                new_defs = await mgr.get_tool_definitions()
                                for nd in new_defs:
                                    if not any(t["function"]["name"] == nd["function"]["name"] for t in tools): tools.append(nd)
                            finally: os.dup2(old_err, stderr_fd)
                        val = "插件已热加载。"
                    elif name == "run_cmd":
                        proc = await asyncio.create_subprocess_shell(args.get("cmd"), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                        o, e = await proc.communicate(); val = f"Out: {o.decode()}\nErr: {e.decode()}"
                    else: val = await mgr.call_tool(name, args)
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "name": name, "content": str(val)})
                
            json.dump({"title": messages[1]["content"][:50], "messages": messages}, open(session_file, 'w', encoding='utf-8'), indent=4, ensure_ascii=False)
        except KeyboardInterrupt: break

async def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("cmd", nargs="*"); p.add_argument("--yolo", action="store_true"); p.add_argument("--version", action="store_true"); p.add_argument("-h", "--help", action="store_true"); p.add_argument("-f", "--file", action="append")
    args, unknown = p.parse_known_args(); full = args.cmd + unknown

    if args.version:
        v = open(VERSION_FILE).read().strip() if os.path.exists(VERSION_FILE) else "v1.1"
        return print(f"AI CLI {v}")

    if args.help or not full:
        UI.banner()
        print(f"{UI.BOLD}{UI.CYAN}🌟 AI CLI 系统：全能型生产力中枢{UI.END}")
        print("-" * 65)
        print(f"\n{UI.BOLD}{UI.YELLOW}💬 核心交互：智力与指令的交汇{UI.END}")
        UI.menu_item("ai [问题...]", "【即时闪答】", "直接输入问题。AI 将利用当前最强模型进行即时推理。")
        UI.menu_item("ai chat", "【全境对话】", "支持“\"\"\"”多行文本与“-f”文件上传。AI 拥有【自主进化】本能，可自行搜寻并安装 MCP 插件。")
        UI.menu_item("ai history", "【时间胶囊】", "调取 ~/.ai/session 历史对话。支持编号加载、'd编号' 销毁记录。")
        
        print(f"\n{UI.BOLD}{UI.YELLOW}⚙️  配置中枢：多供应商与模型矩阵{UI.END}")
        UI.menu_item("ai status", "【实时状态】", "一眼洞察当前活跃供应商、运作模型、限制 AI 权限的工作区路径。")
        UI.menu_item("ai list", "【矩阵概览】", "详细列出驱动引擎（OpenAI/智谱等）、Base URL、模型版本及录入 Key 数量。")
        UI.menu_item("ai new", "【边界扩展】", "引导式添加。支持供应商识别，自动建议保持 URL 并追加 Key。")
        UI.menu_item("ai model", "【思维切换】", "不仅可以切换历史模型，还支持实时录入新模型名称。")
        UI.menu_item("ai switch", "【身份闪切】", "在已有的 AI 供应帝国（DeepSeek, OpenAI 等）之间一秒无缝切换。")
        UI.menu_item("ai delete", "【精准裁撤】", "删除供应商或特定 Key。内置【自动对齐】技术，保持编号完美连续。")
        UI.menu_item("ai workspace", "【领域界定】", "设置 AI 访问边界。所有文件 MCP 工具都将严格受限于此路径。")
        
        print(f"\n{UI.BOLD}{UI.YELLOW}☁️  同步与系统：跨设备一致性{UI.END}")
        UI.menu_item("ai download [url]", "【云端降临】", "从远程 Git (SSH) 叠加合并配置。智能查重，确保多机 Key 自动合一。")
        UI.menu_item("ai update [url]", "【思维上云】", "将本地配置一键推送到远程。严格排除本地运行环境，只同步智能核心。")
        UI.menu_item("ai upgrade [v]", "【版本飞跃】", "一键检测更新。支持指定特定版本号（如 v1.0）进行精准升降级。")
        UI.menu_item("ai uninstall", "【极致清理】", "【自克隆清理】技术。强制杀掉所有 AI 进程并彻底抹除所有足迹。")
        print("-" * 65)
        return

    cmd = full[0].lower()
    if cmd == "new": ConfigManager.setup_new_api()
    elif cmd == "chat":
        ctx = ConfigManager.get_contextual_config(); client, model = await ChatEngine.get_client(ctx)
        if not client: return UI.error("未配置供应商")
        mgr, tools, prompt = await start_mcp_wrapper(args.yolo)
        await start_chat_session(client, model, [{"role": "system", "content": prompt}], tools, mgr, args.yolo, args.file)
    elif cmd == "history":
        ctx = ConfigManager.get_contextual_config(); client, model = await ChatEngine.get_client(ctx)
        if not client: return UI.error("未配置供应商")
        data_list = SessionManager.list_sessions()
        choice = input("\n编号加载 (0 新建, d编号删除, 直接回车退出): ").strip().lower()
        if choice == "0":
            mgr, tools, prompt = await start_mcp_wrapper(args.yolo); await start_chat_session(client, model, [{"role": "system", "content": prompt}], tools, mgr, args.yolo, None)
        elif choice.startswith("d"):
            try: SessionManager.delete_session(data_list[int(choice[1:])-1][0])
            except: pass
        elif choice.isdigit():
            idx = int(choice)-1
            if 0 <= idx < len(data_list):
                mgr, tools, prompt = await start_mcp_wrapper(args.yolo)
                await start_chat_session(client, model, data_list[idx][1]["messages"], tools, mgr, args.yolo, None, os.path.join(SESSION_DIR, data_list[idx][0]))
    elif cmd == "status":
        c = ConfigManager.load_config(); curr = c.get("current_provider", "未设置")
        UI.section("当前运行状态矩阵")
        print(f"活跃供应商  : {UI.BOLD}{UI.CYAN}{curr}{UI.END}")
        print(f"当前运作模型 : {UI.BOLD}{UI.GREEN}{c['provider_settings'].get(curr, {}).get('current_model', '未设置')}{UI.END}")
        print(f"权限工作区   : {UI.BOLD}{UI.YELLOW}{ConfigManager.get_current_workspace()}{UI.END}")
    elif cmd == "model": ConfigManager.manage_model()
    elif cmd == "list": ConfigManager.show_list()
    elif cmd == "delete": ConfigManager.delete_config()
    elif cmd == "download": SyncManager.git_sync(full[1], "download") if len(full)>1 else print("用法: ai download [git-url]")
    elif cmd == "update": SyncManager.git_sync(full[1], "update") if len(full)>1 else print("用法: ai update [git-url]")
    elif cmd == "workspace":
        if len(full)>1: ConfigManager.set_workspace(full[1])
        else: print(f"当前工作区: {ConfigManager.get_current_workspace()}")
    elif cmd == "upgrade": SystemManager.upgrade(full[1] if len(full)>1 else None)
    elif cmd == "uninstall": SystemManager.uninstall()
    elif cmd == "switch":
        cfg = ConfigManager.load_config()
        ps = ConfigManager.get_provider_dirs()
        UI.section("选择目标供应身份")
        for i, p in enumerate(ps): UI.menu_item(str(i+1), p)
        try:
            choice = input("\n请选择编号: ").strip()
            if choice:
                cfg["current_provider"] = ps[int(choice)-1]
                ConfigManager.save_config(cfg); UI.success(f"已闪切至: {cfg['current_provider']}")
        except: pass
    else:
        ctx = ConfigManager.get_contextual_config(); client, model = await ChatEngine.get_client(ctx)
        if not client: return UI.error("未配置供应商")
        mgr, tools, prompt = await start_mcp_wrapper(args.yolo)
        msgs = [{"role": "system", "content": prompt}, {"role": "user", "content": " ".join(full)}]
        if args.file:
            for f in args.file:
                if os.path.exists(f): msgs.insert(1, {"role": "user", "content": f"附件内容 {f}:\n{open(f, 'r', encoding='utf-8', errors='ignore').read()}"})
        await ChatEngine.chat_completion(client, model, msgs, tools, mgr, stream=True, yolo=args.yolo)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
