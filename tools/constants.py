import os, sys

CONFIG_DIR = os.path.expanduser("~/.config/ai")
USER_AI_DIR = os.path.expanduser("~/.ai")
SESSION_DIR = os.path.join(USER_AI_DIR, "session")
MCP_SERVERS_DIR = os.path.join(USER_AI_DIR, "mcp_servers")

IS_WINDOWS = sys.platform.startswith("win")

def get_base_dir():
    cfg_file = os.path.join(CONFIG_DIR, 'base_path.config')
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, 'r', encoding='utf-8-sig') as f:
                path = f.read().strip().replace('"', '').replace("'", "")
                if IS_WINDOWS and len(path) > 2 and path[1:3] == " :": path = path[0] + ":" + path[3:]
                return path
        except: pass
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = get_base_dir()
VERSION_FILE = os.path.join(BASE_DIR, "version.txt")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
MCP_CONFIG = os.path.join(CONFIG_DIR, "mcp_config.json")
WORKSPACE_CONFIG = os.path.join(CONFIG_DIR, "workspace.config")

LIBRARY_DRIVERS = {"1": "openai", "2": "zhipuai", "3": "groq", "4": "dashscope", "5": "anthropic"}
