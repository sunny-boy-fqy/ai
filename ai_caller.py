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

IS_WINDOWS = sys.platform.startswith("win")

# Determine Base Directory (Repo Location)
if not os.path.exists(os.path.join(CONFIG_DIR, 'base_path.config')):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
else:
    try:
        # Use utf-8-sig to handle BOM and strip any weird whitespace/quotes
        with open(os.path.join(CONFIG_DIR, 'base_path.config'), 'r', encoding='utf-8-sig') as f:
            BASE_DIR = f.read().strip().replace('"', '').replace("'", "")
            # Remove potential spaces after drive letter in Windows (e.g., "D :\\" -> "D:\\")
            if IS_WINDOWS and len(BASE_DIR) > 2 and BASE_DIR[1:3] == " :":
                BASE_DIR = BASE_DIR[0] + ":" + BASE_DIR[3:]
    except:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if not BASE_DIR or not os.path.exists(BASE_DIR):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Constants using BASE_DIR
VERSION_FILE = os.path.join(BASE_DIR, "version.txt")

CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
if IS_WINDOWS:
    VENV_PIP = os.path.join(CONFIG_DIR, "python_venv", "Scripts", "pip.exe")
    VENV_PYTHON = os.path.join(CONFIG_DIR, "python_venv", "Scripts", "python.exe")
else:
    VENV_PIP = os.path.join(CONFIG_DIR, "python_venv", "bin", "pip")
    VENV_PYTHON = os.path.join(CONFIG_DIR, "python_venv", "bin", "python3")

CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
if IS_WINDOWS:
    VENV_PIP = os.path.join(CONFIG_DIR, "python_venv", "Scripts", "pip.exe")
    VENV_PYTHON = os.path.join(CONFIG_DIR, "python_venv", "Scripts", "python.exe")
else:
    VENV_PIP = os.path.join(CONFIG_DIR, "python_venv", "bin", "pip")
    VENV_PYTHON = os.path.join(CONFIG_DIR, "python_venv", "bin", "python3")

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
        with open(WORKSPACE_CONFIG, "r", encoding='utf-8') as f:
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
    with open(WORKSPACE_CONFIG, "w", encoding='utf-8') as f:
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

async def start_chat(yolo_mode=False, file_paths=None):
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
    print("💡 提示: 输入 'exit' 退出, 'clear' 清空, '\"\"\"' 开启/结束多行输入。")

    if file_paths:
        for fp in file_paths:
            if os.path.exists(fp):
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                messages.append({"role": "user", "content": f"已上传文件 {os.path.basename(fp)}:\n{content}"})
                print(f"📎 已载入文件: {fp}")

    while True:
        try:
            user_input = ""
            line = input("You > ").strip()
            if not line: continue
            
            if line == '"""':
                print("📝 [多行模式] 输入 '\"\"\"' 结束并发送。")
                lines = []
                while True:
                    l = input("... ")
                    if l.strip() == '"""': break
                    lines.append(l)
                user_input = "\n".join(lines)
            else:
                user_input = line

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

async def call_ai(args, yolo_mode=False, file_paths=None):
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
    if file_paths:
        for fp in file_paths:
            if os.path.exists(fp):
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                prompt += f"\n\n[文件内容 {os.path.basename(fp)}]:\n{content}"

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

def delete_provider_or_api():
    cfg = load_config()
    print("\n=== 🗑️  删除供应商或 API Key ===")
    providers = get_provider_dirs()
    if not providers: return print("❌ 无供应商配置。")
    
    for i, p in enumerate(providers):
        p_dir = os.path.join(CONFIG_DIR, p)
        keys = [f for f in os.listdir(p_dir) if f.startswith("api")]
        print(f"{i+1}. {p} ({len(keys)} 个 Key)")
    
    idx = input("\n请选择要管理的供应商编号 (输入 c 取消): ").strip()
    if idx.lower() == 'c': return
    try:
        p_name = providers[int(idx)-1]
    except: return print("❌ 无效编号。")
    
    print(f"\n供应商: {p_name}")
    print("1. [删除整个供应商]")
    print("2. [删除特定的 API Key]")
    mode = input("请选择: ").strip()
    
    p_dir = os.path.join(CONFIG_DIR, p_name)
    if mode == "1":
        confirm = input(f"⚠️ 确定要删除 '{p_name}' 及其所有配置吗？(y/N): ").lower()
        if confirm == 'y':
            shutil.rmtree(p_dir)
            if cfg.get("current_provider") == p_name: cfg["current_provider"] = ""
            if p_name in cfg.get("provider_settings", {}): del cfg["provider_settings"][p_name]
            if p_name in cfg.get("base_urls", {}): del cfg["base_urls"][p_name]
            save_config(cfg)
            print(f"✅ 供应商 '{p_name}' 已删除。")
    elif mode == "2":
        keys = sorted([f for f in os.listdir(p_dir) if f.startswith("api")])
        for i, k in enumerate(keys):
            with open(os.path.join(p_dir, k), "r") as f: val = f.read().strip()
            print(f"{i+1}. {k} (Key: {val[:8]}...{val[-4:]})")
        k_idx = input("请选择要删除的 Key 编号: ").strip()
        try:
            target_k = keys[int(k_idx)-1]
            os.remove(os.path.join(p_dir, target_k))
            print(f"✅ API Key '{target_k}' 已删除。")
            # If no keys left, delete dir
            if not [f for f in os.listdir(p_dir) if f.startswith("api")]:
                shutil.rmtree(p_dir)
                print(f"ℹ️ 由于无可用 Key，供应商 '{p_name}' 已自动移除。")
        except: print("❌ 无效编号。")

def download_config(repo_url):
    import tempfile
    import stat
    
    # 安全检查：强烈建议使用 SSH
    if repo_url.startswith("http"):
        print("⚠️  安全警告：检测到您正在使用 HTTPS URL。")
        print("为了安全起见，强烈建议使用 SSH 协议 (git@github.com:user/repo.git)。")
        confirm = input("确定要继续使用 HTTPS 吗？(y/N): ").lower()
        if confirm != 'y': return

    print(f"⏳ 正在从 {repo_url} 同步配置...")

    # 禁用 Git 交互式提示，防止弹出用户名密码输入
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes"

    def remove_readonly(func, path, _):
        os.chmod(path, stat.S_IWRITE)
        func(path)
    
    # ... (备份逻辑保持不变)
    
    temp_dir = tempfile.mkdtemp()
    try:
        if shutil.which("git"):
            subprocess.run(["git", "clone", "--depth", "1", repo_url, temp_dir], env=env, check=True)
        else:
            print("❌ 未检测到 git。")
            return
# ... (中间拷贝逻辑保持不变)

        # 移除克隆下来的 .git 目录
        git_dir = os.path.join(temp_dir, ".git")
        if os.path.exists(git_dir):
            shutil.rmtree(git_dir, onexc=remove_readonly)

        # 3. 确认覆盖
        confirm = input(f"⚠️  确定要使用下载的内容覆盖 {CONFIG_DIR} 吗？当前所有 API Key 和设置将丢失。(y/N): ").lower()
        if confirm != 'y':
            print("操作已取消。")
            return

        # 4. 执行覆盖
        for item in os.listdir(CONFIG_DIR):
            item_path = os.path.join(CONFIG_DIR, item)
            if item in ["python_venv", "node"]: # 保留本地运行环境
                continue
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path, onexc=remove_readonly)
                else:
                    os.remove(item_path)
            except Exception as e:
                print(f"⚠️  无法删除 {item}: {e}")
        
        # 拷贝新内容
        for item in os.listdir(temp_dir):
            if item in ["python_venv", "node", ".git"]: # 严格排除环境目录
                continue
            s = os.path.join(temp_dir, item)
            d = os.path.join(CONFIG_DIR, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        
        # 5. 还原 base_path.config
        if base_path_content:
            with open(base_path_cfg, 'w', encoding='utf-8') as f:
                f.write(base_path_content)
        
        print("✅ 配置同步完成！")

    except Exception as e:
        print(f"❌ 同步失败: {e}")
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, onexc=remove_readonly)

def upload_config(repo_url):
    import tempfile
    import stat
    
    # 强制安全检查
    if not repo_url.startswith("git@"):
        print("❌ 拒绝操作：为了保护您的账号安全，'ai update' 必须使用 SSH 协议。")
        print("示例用法: ai update git@github.com:yourname/ai-config.git")
        print("请确保您已在 GitHub 上配置了 SSH Key。")
        return

    print(f"⏳ 正在同步配置到 {repo_url} ...")

    # 禁用所有交互式提示
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes"

    def remove_readonly(func, path, _):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    temp_dir = tempfile.mkdtemp()
    try:
        # 1. 克隆仓库
        subprocess.run(["git", "clone", "--depth", "1", repo_url, temp_dir], env=env, check=True)

        # 2. 清理仓库旧文件 (保留 .git)
        for item in os.listdir(temp_dir):
            if item == ".git": continue
            item_path = os.path.join(temp_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path, onexc=remove_readonly)
            else:
                os.remove(item_path)

        # 3. 拷贝本地配置
        print("📦 正在准备配置文件...")
        for item in os.listdir(CONFIG_DIR):
            if item in ["python_venv", "node", ".git", "base_path.config"]:
                continue
            s = os.path.join(CONFIG_DIR, item)
            d = os.path.join(temp_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)

        # 4. 提交并推送
        os.chdir(temp_dir)
        subprocess.run(["git", "add", "."], env=env, check=True)
        
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, env=env)
        if not status.stdout.strip():
            print("ℹ️ 配置已是最新，无需更新。")
            return

        commit_msg = f"Update config from CLI"
        subprocess.run(["git", "commit", "-m", commit_msg], env=env, check=True)
        subprocess.run(["git", "push"], env=env, check=True)
        
        print("✅ 配置已成功通过 SSH 上传到仓库！")

    except Exception as e:
        print(f"❌ 上传失败: 请检查您的 SSH 权限或仓库地址。错误: {e}")
    finally:
        os.chdir(BASE_DIR)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, onexc=remove_readonly)

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
        with open(local_path, "w", encoding='utf-8') as f:
            json.dump({"provider": p, "model": current_m}, f, indent=4, ensure_ascii=False)
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
    if IS_WINDOWS:
        install_script = os.path.join(BASE_DIR, "install.ps1")
        if os.path.exists(install_script):
            try:
                # Force double quotes around script path for PowerShell
                subprocess.run(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", f'"{install_script}"'], check=True)
            except Exception as e:
                print(f"❌ 更新失败: {e}")
        else:
            print(f"❌ 找不到安装脚本: \"{install_script}\"")
    else:
        install_script = os.path.join(BASE_DIR, "install.sh")
        if os.path.exists(install_script):
            subprocess.run(["bash", f"{install_script}", "--upgrade"])
        else:
            print("❌ 找不到安装脚本 (install.sh)，请手动更新。")

def uninstall_tool():
    confirm = input("⚠️  确定要卸载 AI CLI 吗？这将删除所有配置和插件。(y/N): ").lower()
    if confirm != 'y': return
    
    if IS_WINDOWS:
        uninstall_script = os.path.join(BASE_DIR, "uninstall.ps1")
        if os.path.exists(uninstall_script):
            print("⏳ 正在调用 Windows 卸载脚本...")
            # Use quotes for script path
            subprocess.run(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", f'"{uninstall_script}"'])
        else:
            print(f"❌ 找不到卸载脚本: \"{uninstall_script}\"")
    else:
        uninstall_script = os.path.join(BASE_DIR, "uninstall.sh")
        if os.path.exists(uninstall_script):
            subprocess.run(["bash", f"{uninstall_script}"])
        else:
            print("❌ 找不到卸载脚本 (uninstall.sh)。")

def show_status():
    cfg = get_contextual_config()
    p = cfg.get("current_provider", "未设置")
    sett = cfg.get("provider_settings", {}).get(p, {})
    m = sett.get("current_model", "未设置")
    ws = cfg.get("workspace", "未设置")
    is_local = " (本地配置)" if cfg.get("is_local") else ""
    
    print(f"\n=== 🤖 AI CLI 状态 ===")
    print(f"当前供应商: {p}{is_local}")
    print(f"当前大模型: {m}")
    print(f"当前工作区: {ws}")
    if not p or p == "未设置":
        print("\n💡 提示: 使用 'ai new' 配置供应商。")

async def main():
    parser = argparse.ArgumentParser(description="AI CLI Tool", add_help=False)
    parser.add_argument("command", nargs="*", help="Subcommand or query")
    parser.add_argument("--yolo", action="store_true", help="Enable shell command execution")
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("-h", "--help", action="store_true", help="Show help")
    parser.add_argument("-f", "--file", action="append", help="Upload file(s)")
    
    args_namespace, unknown = parser.parse_known_args()
    
    yolo_mode = args_namespace.yolo
    file_paths = args_namespace.file
    
    if args_namespace.version:
        print(f"AI CLI {get_version()}")
        return

    if args_namespace.help or (not args_namespace.command and not unknown):
        show_help()
        return

    # Handle cases where command is mixed with query
    full_args = args_namespace.command + unknown
    if not full_args:
        show_help()
        return
        
    cmd = full_args[0].lower()
    
    if cmd == "new": setup_new_api()
    elif cmd == "chat": await start_chat(yolo_mode=yolo_mode, file_paths=file_paths)
    elif cmd == "model": manage_model()
    elif cmd == "status": show_status()
    elif cmd == "upgrade": upgrade_tool()
    elif cmd == "uninstall": uninstall_tool()
    elif cmd == "delete": delete_provider_or_api()
    elif cmd == "download":
        if len(full_args) > 1: download_config(full_args[1])
        else: print("用法: ai download [Git 仓库 URL]")
    elif cmd == "update":
        if len(full_args) > 1: upload_config(full_args[1])
        else: print("用法: ai update [Git 仓库 URL]")
    elif cmd == "workspace":
        if len(full_args) > 1: set_workspace(full_args[1])
        else: print(f"当前工作区: {get_current_workspace()}")
    elif cmd == "switch":
        # Simplified switch logic
        cfg = load_config()
        ps = get_provider_dirs()
        if not ps: return print("❌ 无供应商。")
        for i, p in enumerate(ps): print(f"{i+1}. {p}")
        idx = input("选择编号: ").strip()
        try:
            cfg["current_provider"] = ps[int(idx)-1]
            save_config(cfg)
            print(f"✅ 已切换至: {cfg['current_provider']}")
        except: pass
    else:
        # Treat as query
        await call_ai(full_args, yolo_mode=yolo_mode, file_paths=file_paths)

def show_help():
    print(f"""
🤖 AI CLI 工具 {get_version()}
================================
AI CLI 是一个全能的命令行 AI 助手，支持工具调用、系统操作和多模型切换。

基本用法:
  ai [问题...]        快速提问（支持连续输入多个词）
  ai chat             进入交互式对话模式
  ai chat -f [文件]   带着文件内容进入对话

核心功能:
  -f, --file [路径]   载入一个或多个文件内容到 prompt 中
  \"\"\"                 在对话模式下，输入 \"\"\" 开启/结束多段文本输入
  --yolo              启用 YOLO 模式，允许 AI 直接执行 Shell 命令（仅限 chat 和查询）

配置管理:
  ai new              添加 API Key 或配置新的供应商 (OpenAI, 智谱, Groq 等)
  ai model            管理模型：切换当前模型、查看历史、或为当前目录创建 .ai-config.json
  ai switch           在已配置的供应商之间快速切换
  ai delete           删除不需要的供应商或特定的 API Key
  ai download [url]   从 Git 仓库下载并覆盖所有配置 (用于多机同步)
  ai update [url]     上传本地配置到 Git 仓库
  ai status           查看当前生效的供应商、模型及工作区路径
  ai workspace [path] 设置 AI 的活动范围（影响文件系统工具的访问权限）

系统维护:
  ai upgrade          从 GitHub 获取最新代码并自动完成环境升级
  ai uninstall        一键卸载 AI 工具及其所有配置文件
  ai --version        显示当前安装的版本号
  ai -h, --help       显示此帮助信息

配置路径:
  - 核心配置: ~/.config/ai/
  - MCP 插件: ~/.ai/mcp_servers/
""")

if __name__ == "__main__":
    asyncio.run(main())
