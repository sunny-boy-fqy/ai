#!/usr/bin/env python3
import sys, os, asyncio, argparse
from datetime import datetime

# 将当前目录加入 path 以便导入 tools
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.constants import VERSION_FILE, MCP_CONFIG
from tools.ui import UI
from tools.config_mgr import ConfigManager
from tools.mcp_mgr import MCPManager
from tools.session_mgr import SessionManager
from tools.chat_engine import ChatEngine, MCPToolManager
from tools.sync_mgr import SyncManager
from tools.sys_mgr import SystemManager

async def start_mcp_wrapper(yolo):
    if not MCPToolManager: return None, [], "你是助手。"
    mgr = MCPToolManager(MCP_CONFIG); ws = ConfigManager.get_current_workspace()
    try:
        await mgr.initialize_tools(allowed_paths=[ws])
        tools = await mgr.get_tool_definitions()
    except: tools = []
    
    # 自主扩展能力
    tools.append({"type":"function", "function":{"name":"install_plugin", "description":"搜索并安装新能力插件", "parameters":{"type":"object","properties":{"name":{"type":"string","enum":list(MCPManager.fetch_mcp_market().keys())}},"required":["name"]}}})
    if yolo:
        tools.append({"type":"function", "function":{"name":"run_cmd", "description":"执行终端命令", "parameters":{"type":"object","properties":{"cmd":{"type":"string"}},"required":["cmd"]}}})
    
    return mgr, tools, f"你是 AI CLI。当前工作区: {ws}。"

async def start_chat_session(client, model, messages, tools, mgr, yolo, files, session_file=None):
    if not session_file:
        from tools.constants import SESSION_DIR
        session_file = os.path.join(SESSION_DIR, f"s_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    UI.section("对话就绪")
    if files:
        for f in files:
            if os.path.exists(f):
                content = open(f, 'r', encoding='utf-8', errors='ignore').read()
                messages.append({"role": "user", "content": f"文件 {f}:\n{content}"})
                UI.info(f"已载入文件: {f}")
    
    while True:
        try:
            line = input("\nYou > ").strip()
            if not line: continue
            if line == '"""':
                print("📝 [多行模式] 输入 '\"\"\"' 结束并发送。"); lines = []
                while True:
                    l = input("... "); 
                    if l.strip() == '"""': break
                    lines.append(l)
                inp = "\n".join(lines)
            else: inp = line
            if inp.lower() in ["exit", "quit"]: break
            if inp.lower() == "clear":
                messages = [messages[0]]
                UI.success("上下文已清理。")
                continue
            
            messages.append({"role": "user", "content": inp})
            print(f"{UI.CYAN}AI > {UI.END}", end="", flush=True)
            full = await ChatEngine.chat_completion(client, model, messages, tools, mgr, stream=True, yolo=yolo, session_file=session_file)
            messages.append({"role": "assistant", "content": full})
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
        print("💡 基础对话:")
        UI.menu_item("ai [问题]", "单次提问")
        UI.menu_item("ai chat", "进入对话模式")
        UI.menu_item("ai history", "查看历史会话")
        print("\n⚙️  配置管理:")
        UI.menu_item("ai status", "查看当前活跃状态")
        UI.menu_item("ai list", "列出所有供应商")
        UI.menu_item("ai new", "配置 Key/供应商")
        UI.menu_item("ai model", "管理/切换模型")
        UI.menu_item("ai switch", "快速切换供应商")
        UI.menu_item("ai delete", "删除供应商/Key")
        UI.menu_item("ai workspace", "设置文件访问工作区")
        print("\n☁️  系统与同步:")
        UI.menu_item("ai download [url]", "同步配置(叠加模式)")
        UI.menu_item("ai update [url]", "上传配置(叠加模式)")
        UI.menu_item("ai upgrade [v]", "系统升级")
        UI.menu_item("ai uninstall", "彻底卸载")
        return

    cmd = full[0].lower()
    if cmd == "new": ConfigManager.setup_new_api()
    elif cmd == "chat":
        ctx = ConfigManager.get_contextual_config(); client, model = await ChatEngine.get_client(ctx)
        if not client: return UI.error("未配置供应商，请运行 ai new")
        mgr, tools, prompt = await start_mcp_wrapper(args.yolo)
        await start_chat_session(client, model, [{"role": "system", "content": prompt}], tools, mgr, args.yolo, args.file)
    elif cmd == "history":
        ctx = ConfigManager.get_contextual_config(); client, model = await ChatEngine.get_client(ctx)
        if not client: return UI.error("请先配置供应商")
        data_list = SessionManager.list_sessions()
        choice = input("\n请选择加载编号 (0 新建, d编号删除): ").strip().lower()
        if choice == "0":
            mgr, tools, prompt = await start_mcp_wrapper(args.yolo)
            await start_chat_session(client, model, [{"role": "system", "content": prompt}], tools, mgr, args.yolo, None)
        elif choice.startswith("d"):
            try: SessionManager.delete_session(data_list[int(choice[1:])-1][0])
            except: pass
        elif choice.isdigit():
            idx = int(choice)-1
            if 0 <= idx < len(data_list):
                mgr, tools, prompt = await start_mcp_wrapper(args.yolo)
                from tools.constants import SESSION_DIR
                await start_chat_session(client, model, data_list[idx][1]["messages"], tools, mgr, args.yolo, None, os.path.join(SESSION_DIR, data_list[idx][0]))
    elif cmd == "status":
        c = ConfigManager.load_config(); curr = c.get("current_provider", "未设置")
        UI.section("当前运行状态")
        print(f"活跃供应商: {UI.BOLD}{curr}{UI.END}")
        print(f"当前大模型: {c['provider_settings'].get(curr, {}).get('current_model', '未设置')}")
        print(f"工作区目录: {ConfigManager.get_current_workspace()}")
    elif cmd == "list": ConfigManager.show_list()
    elif cmd == "model": ConfigManager.manage_model()
    elif cmd == "delete": ConfigManager.delete_config()
    elif cmd == "download": SyncManager.git_sync(full[1], "download") if len(full)>1 else print("ai download [url]")
    elif cmd == "update": SyncManager.git_sync(full[1], "update") if len(full)>1 else print("ai update [url]")
    elif cmd == "workspace":
        if len(full)>1: ConfigManager.set_workspace(full[1])
        else: print(f"当前工作区: {ConfigManager.get_current_workspace()}")
    elif cmd == "upgrade": SystemManager.upgrade(full[1] if len(full)>1 else None)
    elif cmd == "uninstall": SystemManager.uninstall()
    elif cmd == "switch":
        cfg = ConfigManager.load_config(); ps = ConfigManager.get_provider_dirs()
        UI.section("切换活跃供应商")
        for i, p in enumerate(ps): UI.menu_item(str(i+1), p)
        try:
            cfg["current_provider"] = ps[int(input("\n请选择编号: "))-1]
            ConfigManager.save_config(cfg); UI.success(f"已切换至: {cfg['current_provider']}")
        except: pass
    else:
        # 单次问答
        ctx = ConfigManager.get_contextual_config(); client, model = await ChatEngine.get_client(ctx)
        if not client: return UI.error("未配置供应商")
        mgr, tools, prompt = await start_mcp_wrapper(args.yolo)
        msgs = [{"role": "system", "content": prompt}, {"role": "user", "content": " ".join(full)}]
        if args.file:
            for f in args.file:
                if os.path.exists(f):
                    content = open(f, 'r', encoding='utf-8', errors='ignore').read()
                    msgs.insert(1, {"role": "user", "content": f"文件 {f}:\n{content}"})
        await ChatEngine.chat_completion(client, model, msgs, tools, mgr, yolo=args.yolo)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
