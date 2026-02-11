#!/usr/bin/env python3
import sys
import os
import json
import subprocess
import shutil
import asyncio
import re
import argparse

# --- Constants & Configuration Paths ---
CONFIG_DIR = os.path.expanduser("~/.config/ai")
USER_AI_DIR = os.path.expanduser("~/.ai")
MCP_SERVERS_DIR = os.path.join(USER_AI_DIR, "mcp_servers")

# Ensure base paths exist
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(MCP_SERVERS_DIR, exist_ok=True)

# Determine Base Directory (Repo Location)
if not os.path.exists(os.path.join(CONFIG_DIR, 'base_path.config')):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
else:
    with open(os.path.join(CONFIG_DIR, 'base_path.config'), 'r') as f:
        BASE_DIR = f.read().strip()

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
VENV_PIP = os.path.join(CONFIG_DIR, "python_venv/bin/pip")
MCP_CONFIG = os.path.join(CONFIG_DIR, "mcp_config.json")
WORKSPACE_CONFIG = os.path.join(CONFIG_DIR, "workspace.config")

# Import MCP support
try:
    from mcp_tools import MCPToolManager
except ImportError:
    MCPToolManager = None

# Default Library Drivers
LIBRARY_DRIVERS = {
    "1": "openai",
    "2": "zhipuai",
    "3": "groq",
    "4": "dashscope",
    "5": "anthropic"
}

# --- Configuration Management ---

def load_config():
    """Loads global configuration."""
    if not os.path.exists(CONFIG_PATH):
        return {"current_provider": "", "provider_settings": {}, "base_urls": {}}
    try:
        with open(CONFIG_PATH, "r", encoding='utf-8') as f:
            cfg = json.load(f)
            return cfg
    except:
        return {"current_provider": "", "provider_settings": {}, "base_urls": {}}

def save_config(cfg):
    """Saves global configuration."""
    with open(CONFIG_PATH, "w", encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

def get_current_workspace():
    """Gets the active workspace directory."""
    if os.path.exists(WORKSPACE_CONFIG):
        with open(WORKSPACE_CONFIG, "r") as f:
            ws = f.read().strip()
            if os.path.isdir(ws):
                return ws
    return os.getcwd()

def set_workspace(path):
    """Sets the active workspace."""
    abs_path = os.path.abspath(path)
    if not os.path.isdir(abs_path):
        print(f"❌ Error: Directory '{abs_path}' does not exist.")
        return
    with open(WORKSPACE_CONFIG, "w") as f:
        f.write(abs_path)
    print(f"✅ Workspace set to: {abs_path}")

def get_contextual_config():
    """
    Merges global config with local .ai-config.json.
    Local config overrides provider and model.
    """
    global_cfg = load_config()
    
    # Check for local config in current workspace
    workspace = get_current_workspace()
    local_config_path = os.path.join(workspace, ".ai-config.json")
    
    context = global_cfg.copy()
    context["is_local"] = False
    context["workspace"] = workspace

    if os.path.exists(local_config_path):
        try:
            with open(local_config_path, "r") as f:
                local_cfg = json.load(f)
                if "provider" in local_cfg:
                    context["current_provider"] = local_cfg["provider"]
                    context["is_local"] = True
                if "model" in local_cfg:
                    # We need to temporarily patch the provider settings to reflect the local model choice
                    p = context.get("current_provider")
                    if p:
                        if "provider_settings" not in context:
                            context["provider_settings"] = {}
                        if p not in context["provider_settings"]:
                            context["provider_settings"][p] = {}
                        context["provider_settings"][p]["current_model"] = local_cfg["model"]
                        context["is_local"] = True
        except Exception as e:
            print(f"⚠️ Failed to load local config: {e}")
            
    return context

# --- Tool Definitions (Built-in) ---

async def run_shell_command_tool(command):
    """Executes a shell command."""
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return f"Stdout:\n{stdout.decode().strip()}\nStderr:\n{stderr.decode().strip()}"
    except Exception as e:
        return f"Error executing command: {e}"

# --- Core Logic ---

async def get_mcp_context(yolo_mode=False):
    """Initializes MCP tools and returns manager, tools list, and system prompt."""
    if not MCPToolManager:
        return None, [], "你是一个有用的 AI 助手。"
    
    mcp_manager = MCPToolManager(MCP_CONFIG)
    
    # Dynamic workspace restriction for filesystem
    workspace = get_current_workspace()
    allowed_paths = [workspace]
    
    # Hide startup noise
    stderr_fd = sys.stderr.fileno()
    with open(os.devnull, 'w') as devnull:
        old_stderr = os.dup(stderr_fd)
        try:
            os.dup2(devnull.fileno(), stderr_fd)
            # Pass the workspace path to initialize_tools
            # This requires updating mcp_tools.py to accept args! (Done in Step 2)
            await mcp_manager.initialize_tools(allowed_paths=allowed_paths)
            tools = await mcp_manager.get_tool_definitions()
        finally:
            os.dup2(old_stderr, stderr_fd)
            os.close(old_stderr)
    
    # Add Built-in Tools if YOLO mode is on
    if yolo_mode:
        tools.append({
            "type": "function",
            "function": {
                "name": "run_shell_command",
                "description": "Execute a shell command on the host system. Use with CAUTION.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "The command to run"}
                    },
                    "required": ["command"]
                }
            }
        })

    system_prompt = "你是一个有用的 AI 助手。"
    if tools:
        tool_names = [t["function"]["name"] for t in tools]
        system_prompt += f"\n\n你可以访问以下工具: {', '.join(tool_names)}\n"
        system_prompt += f"当前工作区: {workspace}\n"
        system_prompt += "如果你需要查询更多可用的 MCP 工具，请使用 'web-search__search' 或 'web-search__search_news' 搜索 'MCP tools' 或 'Model Context Protocol servers'。\n"
        
        if yolo_mode:
            system_prompt += "⚠️以此模式运行命令（run_shell_command）具有极高权限，请务必谨慎。\n"
        
        system_prompt += "如果你决定使用工具，请优先使用函数调用功能。如果你的环境不支持直接调用函数，请在回复中包含如下格式的内容来请求调用工具：\n"
        system_prompt += "tool_call_name\n[工具名称]\ntool_call_arguments\n[JSON格式的参数]\n"
    
    return mcp_manager, tools, system_prompt

async def chat_completion_with_tools(client, model, messages, tools, mcp_manager, stream=True, yolo_mode=False):
    while True:
        try:
            # Use tools only if available and not already too many tool calls in history to avoid loops
            current_tools = tools if tools else None
            
            # OpenAI API call
            res = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=current_tools,
                tool_choice="auto" if current_tools else None,
                stream=stream
            )

            full_response = ""
            tool_calls = []

            # Handle Stream vs Non-Stream
            if stream:
                for chunk in res:
                    if not hasattr(chunk, 'choices') or not chunk.choices: continue
                    delta = chunk.choices[0].delta
                    if delta.content:
                        content = delta.content
                        print(content, end="", flush=True)
                        full_response += content
                    if delta.tool_calls:
                        for tc_chunk in delta.tool_calls:
                            if len(tool_calls) <= tc_chunk.index:
                                tool_calls.append({
                                    "id": f"call_{tc_chunk.id or len(tool_calls)}",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                })
                            tc = tool_calls[tc_chunk.index]
                            if tc_chunk.id: tc["id"] = tc_chunk.id
                            if tc_chunk.function.name: tc["function"]["name"] += tc_chunk.function.name
                            if tc_chunk.function.arguments: tc["function"]["arguments"] += tc_chunk.function.arguments
                print()
            else:
                choice = res.choices[0]
                full_response = choice.message.content or ""
                print(full_response)
                if choice.message.tool_calls:
                    tool_calls = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                        } for tc in choice.message.tool_calls
                    ]

            # Fallback: Parse text-based tool calls
            if not tool_calls and "tool_call_name" in full_response:
                name_match = re.search(r"tool_call_name\n(.*?)\n", full_response)
                args_match = re.search(r"tool_call_arguments\n({.*?})", full_response, re.DOTALL)
                if name_match and args_match:
                    tool_calls.append({
                        "id": f"text_call_{len(messages)}",
                        "type": "function",
                        "function": {
                            "name": name_match.group(1).strip(),
                            "arguments": args_match.group(1).strip()
                        }
                    })

            if not tool_calls:
                return full_response

            # Append Assistant Response
            messages.append({
                "role": "assistant",
                "content": full_response if full_response else None,
                "tool_calls": tool_calls if "text_call_" not in tool_calls[0]["id"] else None
            })

            # Execute Tool Calls
            for tool_call in tool_calls:
                t_name = tool_call["function"]["name"]
                t_args_str = tool_call["function"]["arguments"]
                try:
                    t_args = json.loads(t_args_str)
                except json.JSONDecodeError:
                    t_args_str = re.sub(r"(\w+):", r"'\1':", t_args_str).replace("'", '"')
                    t_args = json.loads(t_args_str)

                print(f"🛠️  正在调用工具: {t_name} ...")
                
                result = ""
                # Handle Built-in Tools (Shell)
                if t_name == "run_shell_command":
                    if not yolo_mode:
                        result = "Error: Shell commands are disabled. Use --yolo flag to enable."
                    else:
                        result = await run_shell_command_tool(t_args.get("command"))
                else:
                    # Handle MCP Tools (with stderr suppression)
                    stderr_fd = sys.stderr.fileno()
                    with open(os.devnull, 'w') as devnull:
                        old_stderr = os.dup(stderr_fd)
                        try:
                            os.dup2(devnull.fileno(), stderr_fd)
                            result = await mcp_manager.call_tool(t_name, t_args)
                        finally:
                            os.dup2(old_stderr, stderr_fd)
                            os.close(old_stderr)
                
                messages.append({
                    "role": "tool" if "text_call_" not in tool_call["id"] else "user",
                    "tool_call_id": tool_call["id"] if "text_call_" not in tool_call["id"] else None,
                    "name": t_name,
                    "content": f"工具 {t_name} 的返回结果是: {str(result)}" if "text_call_" in tool_call["id"] else str(result)
                })
                print(f"📦 工具返回内容已送达 AI")
            
            if not stream:
                print("⏳ AI 正在思考工具返回的结果...")
            else:
                print(f"AI > ", end="", flush=True)

        except Exception as e:
            print(f"\n❌ 对话出错: {e}")
            return str(e)

# --- CLI Handlers ---

async def start_chat(yolo_mode=False):
    cfg = get_contextual_config()
    p = cfg.get("current_provider")
    if not p: return print("尚未初始化，请输入 'ai new'")
    
    sett = cfg["provider_settings"].get(p, {})
    m = sett.get("current_model")
    driver = sett.get("driver", "openai")
    base_url = cfg["base_urls"].get(p)
    
    # Load keys
    p_dir = os.path.join(CONFIG_DIR, p)
    keys = [f for f in os.listdir(p_dir) if f.startswith("api")] if os.path.exists(p_dir) else []
    if not keys: return print("❌ 找不到 Key。")
    with open(os.path.join(p_dir, keys[0]), "r") as f: kv = f.read().strip()

    # Initialize Client
    try:
        if driver == "zhipuai" and not base_url:
            from zhipuai import ZhipuAI
            c = ZhipuAI(api_key=kv)
        elif driver == "groq" and not base_url:
            from groq import Groq
            c = Groq(api_key=kv)
        else:
            from openai import OpenAI
            c = OpenAI(api_key=kv, base_url=base_url)
    except Exception as e:
        return print(f"❌ 初始化失败: {e}")

    mcp_manager, tools, system_prompt = await get_mcp_context(yolo_mode=yolo_mode)
    messages = [{"role": "system", "content": system_prompt}]
    
    prefix = "[LOCAL] " if cfg.get("is_local") else ""
    print(f"💬 {prefix}进入对话模式 [{p} | {m}] (Workspace: {cfg.get('workspace')})\n")
    if yolo_mode: print("⚠️  YOLO 模式已开启: AI 可以直接运行 Shell 命令！")

    while True:
        try:
            user_input = input("You > ").strip()
            if not user_input: continue
            if user_input.lower() in ["exit", "quit"]: break
            if user_input.lower() == "clear":
                messages = [{"role": "system", "content": system_prompt}]
                print("✨ 对话记录已清空。\n")
                continue
            
            messages.append({"role": "user", "content": user_input})
            print(f"AI > ", end="", flush=True)
            
            full_response = await chat_completion_with_tools(c, m, messages, tools, mcp_manager, stream=True, yolo_mode=yolo_mode)
            messages.append({"role": "assistant", "content": full_response})
        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as e:
            print(f"\n❌ 失败: {e}")

async def call_ai(args, yolo_mode=False):
    quiet = False
    if args and args[0] in ["-q", "--quiet"]:
        quiet = True
        args = args[1:]
    
    cfg = get_contextual_config()
    p = cfg.get("current_provider")
    if not p: return print("尚未初始化，请输入 'ai new'")
    sett = cfg["provider_settings"].get(p, {})
    m = sett.get("current_model")
    driver = sett.get("driver", "openai")
    base_url = cfg["base_urls"].get(p)
    
    p_dir = os.path.join(CONFIG_DIR, p)
    keys = [f for f in os.listdir(p_dir) if f.startswith("api")] if os.path.exists(p_dir) else []
    if not keys: return print("❌ 找不到 Key。")
    with open(os.path.join(p_dir, keys[0]), "r") as f: kv = f.read().strip()
    
    prompt = " ".join(args)
    mcp_manager, tools, system_prompt = await get_mcp_context(yolo_mode=yolo_mode)
    
    if not quiet:
        prefix = "[LOCAL] " if cfg.get("is_local") else ""
        print(f"🚀 {prefix}[{p} | {m}] (Workspace: {cfg.get('workspace')}) 响应中...\n")
        if yolo_mode: print("⚠️  YOLO 模式已开启")

    try:
        if driver == "zhipuai" and not base_url:
            from zhipuai import ZhipuAI
            c = ZhipuAI(api_key=kv)
        elif driver == "groq" and not base_url:
            from groq import Groq
            c = Groq(api_key=kv)
        else:
            from openai import OpenAI
            c = OpenAI(api_key=kv, base_url=base_url)
        
        messages = [{"role":"system", "content": system_prompt}, {"role":"user","content":prompt}]
        await chat_completion_with_tools(c, m, messages, tools, mcp_manager, stream=True, yolo_mode=yolo_mode)
        if not quiet:
            print("\n")
    except Exception as e: 
        if not quiet: print(f"\n❌ 失败: {e}")

# Reuse existing management functions (setup_new_api, manage_model, etc.)
# I will just import them or paste them if needed. 
# Since I am rewriting the file, I need to include them.

def get_provider_dirs():
    if not os.path.exists(CONFIG_DIR): return []
    return sorted([d for d in os.listdir(CONFIG_DIR) if os.path.isdir(os.path.join(CONFIG_DIR, d)) and d not in ["python_venv", ".git", "mcp_servers"]])

def test_connection(driver, key, url, model):
    print(f"\n⏳ 正在验证 {driver} (使用模型 {model})...")
    try:
        if driver == "zhipuai" and not url:
            from zhipuai import ZhipuAI
            c = ZhipuAI(api_key=key)
        elif driver == "groq" and not url:
            from groq import Groq
            c = Groq(api_key=key)
        else:
            from openai import OpenAI
            c = OpenAI(api_key=key, base_url=url)
        c.chat.completions.create(model=model, messages=[{"role": "user", "content": "hi"}], max_tokens=1)
        print("✅ 验证成功！")
        return True
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def setup_new_api():
    cfg = load_config()
    print("\n=== 🛠️  AI 供应商 & API 管理 ===")
    providers = get_provider_dirs()
    print("1. [追加] 为现有的供应商添加更多 API Key")
    print("2. [新增] 配置一个全新的供应商")
    mode = input("请选择 (1/2): ").strip()
    provider_name = ""
    driver_lib = ""
    if mode == "1":
        if not providers: return print("❌ 无供应商。")
        for i, p in enumerate(providers): print(f"{i+1}. {p}")
        idx = input("输入编号: ").strip()
        try:
            provider_name = providers[int(idx)-1]
            driver_lib = cfg["provider_settings"].get(provider_name, {}).get("driver", "openai")
        except: return
    else:
        provider_name = input("供应商名称: ").strip()
        if not provider_name: return
        print("驱动: 1.openai 2.zhipuai 3.groq 4.dashscope 5.anthropic")
        driver_lib = LIBRARY_DRIVERS.get(input("编号: ").strip() or "1", "openai")
    
    key = input(f"API Key: ").strip()
    if not key: return
    url = input(f"Base URL (可选): ").strip() or None
    test_m = input("测试模型名: ").strip()
    
    if not test_connection(driver_lib, key, url, test_m):
        if input("⚠️ 验证失败，是否保存？(y/N): ").lower() != 'y': return
    
    prov_dir = os.path.join(CONFIG_DIR, provider_name)
    os.makedirs(prov_dir, exist_ok=True)
    count = len([f for f in os.listdir(prov_dir) if f.startswith("api")])
    fname = f"api_{count + 1}"
    with open(os.path.join(prov_dir, fname), "w") as f: f.write(key)
    
    if provider_name not in cfg["provider_settings"]:
        cfg["provider_settings"][provider_name] = {"driver": driver_lib, "current_model": test_m, "model_history": [test_m]}
    else:
        if test_m not in cfg["provider_settings"][provider_name]["model_history"]:
            cfg["provider_settings"][provider_name]["model_history"].append(test_m)
    
    if url: cfg["base_urls"][provider_name] = url
    if not cfg.get("current_provider"): cfg["current_provider"] = provider_name
    save_config(cfg)
    print("✅ 配置已保存。")

def manage_model():
    cfg = get_contextual_config() # Use contextual to show what's active
    p = cfg.get("current_provider")
    if not p: return
    
    print(f"\n当前供应商: {p}")
    if cfg.get("is_local"):
        print(f"⚠️  注意：当前正在使用本地目录配置覆盖全局设置。")
        
    settings = cfg["provider_settings"].get(p, {})
    current_m = settings.get("current_model", "未设置")
    history = settings.get("model_history", [])
    
    print(f"当前模型: {current_m}")
    print("\n--- 历史模型 ---")
    for i, h in enumerate(history): print(f"{i+1}. {h}")
    
    print("\nn. [输入并切换新模型]")
    print("l. [为当前目录创建本地配置]")
    
    choice = input("\n操作: ").strip().lower()
    
    if choice == 'l':
        ws = get_current_workspace()
        local_path = os.path.join(ws, ".ai-config.json")
        with open(local_path, "w") as f:
            json.dump({"provider": p, "model": current_m}, f, indent=4)
        print(f"✅ 已在 {ws} 创建本地配置。以后在此目录下运行将优先使用 {p}/{current_m}。")
        return

    # For other operations, we update the GLOBAL config
    global_cfg = load_config()
    glob_settings = global_cfg["provider_settings"].get(p, {})
    glob_history = glob_settings.get("model_history", [])
    
    if choice == 'n':
        new_m = input("模型名称: ").strip()
        if new_m:
            glob_settings["current_model"] = new_m
            if new_m not in glob_history: glob_history.append(new_m)
            glob_settings["model_history"] = glob_history
            global_cfg["provider_settings"][p] = glob_settings
            save_config(global_cfg)
            print(f"✅ 全局模型已更新为: {new_m}")
    elif choice.isdigit():
        try:
            target = history[int(choice)-1]
            glob_settings["current_model"] = target
            global_cfg["provider_settings"][p] = glob_settings
            save_config(global_cfg)
            print(f"✅ 全局模型已切换为: {target}")
        except: pass

VERSION_FILE = os.path.join(BASE_DIR, "version.txt")

def get_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            return f.read().strip()
    return "unknown"

def upgrade_tool():
    print("⏳ 正在检查更新...")
    install_script = os.path.join(BASE_DIR, "install.sh")
    if os.path.exists(install_script):
        # We use the current python to run the shell script to ensure we stay in context if possible
        # but bash is better for install.sh
        subprocess.run(["bash", install_script, "--upgrade"])
    else:
        print("❌ 找不到安装脚本，请手动更新。")

async def main():
    parser = argparse.ArgumentParser(description="AI CLI Tool", add_help=False)
    parser.add_argument("command", nargs="?", help="Subcommand or query")
    parser.add_argument("--yolo", action="store_true", help="Enable shell command execution")
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("-h", "--help", action="store_true", help="Show help")
    
    args = sys.argv[1:]
    yolo_mode = False
    if "--yolo" in args:
        yolo_mode = True
        args.remove("--yolo")
    
    if "--version" in args:
        print(f"AI CLI {get_version()}")
        return

    if not args or args[0] in ["-h", "--help"]:
        show_help()
        return

    cmd = args[0].lower()
    
    if cmd == "new": setup_new_api()
    elif cmd == "chat": await start_chat(yolo_mode=yolo_mode)
    elif cmd == "model": manage_model()
    elif cmd == "upgrade": upgrade_tool()
    elif cmd == "workspace":
        if len(args) > 1: set_workspace(args[1])
        else: print(f"当前工作区: {get_current_workspace()}")
    elif cmd == "switch":
        # Simplified switch logic
        cfg = load_config()
        ps = get_provider_dirs()
        for i, p in enumerate(ps): print(f"{i+1}. {p}")
        idx = input("选择: ").strip()
        try:
            cfg["current_provider"] = ps[int(idx)-1]
            save_config(cfg)
            print(f"✅ 已切换至: {cfg['current_provider']}")
        except: pass
    else:
        # Treat as query
        await call_ai(args, yolo_mode=yolo_mode)

def show_help():
    print(f"""
🤖 AI CLI 工具 {get_version()}
================================
基本用法:
  ai [问题]            快速提问
  ai chat             进入对话模式
  ai chat --yolo      进入 YOLO 模式 (允许执行 Shell 命令)

配置管理:
  ai new              添加/配置供应商
  ai model            切换模型 / 创建本地配置
  ai switch           切换供应商
  ai workspace [path] 设置工作区 (限制文件访问范围)

系统命令:
  ai upgrade          更新至最新版本
  ai --version        显示版本号

高级功能:
  --yolo              允许 AI 执行系统命令 (慎用!)
  .ai-config.json     在项目根目录创建此文件可覆盖全局配置

配置存储: ~/.config/ai/
MCP 服务器: ~/.ai/mcp_servers/
""")

if __name__ == "__main__":
    asyncio.run(main())
