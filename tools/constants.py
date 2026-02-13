"""
AI CLI 常量配置
配置结构：
~/.config/ai/
|-- python_venv/     # Python环境
|-- node_venv/       # Node.js环境
|-- mcp/             # MCP插件
|   |-- mcp.config   # MCP配置
|-- base_path.config # AI目录路径
|-- config/          # 供应商配置
|   |-- <供应商>/
|   |   |-- api      # API密钥列表
|   |   |-- url      # Base URL
|   |   |-- model    # 模型列表
|   |-- using.config # 当前使用配置
|-- history/         # 对话历史
"""

import os
import sys

# 基础目录
CONFIG_DIR = os.path.expanduser("~/.config/ai")
USER_AI_DIR = os.path.expanduser("~/ai")

# 子目录
VENV_DIR = os.path.join(CONFIG_DIR, "python_venv")
NODE_DIR = os.path.join(CONFIG_DIR, "node_venv")
MCP_DIR = os.path.join(CONFIG_DIR, "mcp")
CONFIG_SUBDIR = os.path.join(CONFIG_DIR, "config")
HISTORY_DIR = os.path.join(CONFIG_DIR, "history")

# 配置文件
BASE_PATH_FILE = os.path.join(CONFIG_DIR, "base_path.config")
USING_CONFIG_FILE = os.path.join(CONFIG_SUBDIR, "using.config")
MCP_CONFIG_FILE = os.path.join(MCP_DIR, "mcp.config")
PLUGIN_CACHE_FILE = os.path.join(CONFIG_DIR, "plugin_cache.json")

# 版本
with open(os.path.join(USER_AI_DIR, "version.txt"), 'r', encoding='utf-8') as f:
    VERSION = f.read()
    print(VERSION)
REPO_URL = "https://github.com/sunny-boy-fqy/ai.git"

# 系统检测
IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")
IS_MAC = sys.platform.startswith("darwin")


def get_base_dir():
    """获取AI安装目录"""
    if os.path.exists(BASE_PATH_FILE):
        try:
            with open(BASE_PATH_FILE, 'r', encoding='utf-8') as f:
                path = f.read().strip()
                if path and os.path.isdir(path):
                    return path
        except:
            pass
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_venv_python():
    """获取虚拟环境Python路径"""
    if IS_WINDOWS:
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python3")


def get_node_path():
    """获取本地Node.js路径"""
    if IS_WINDOWS:
        return os.path.join(NODE_DIR, "node.exe")
    return os.path.join(NODE_DIR, "bin", "node")


def get_npx_path():
    """获取本地npx路径"""
    if IS_WINDOWS:
        return os.path.join(NODE_DIR, "npx.cmd")
    return os.path.join(NODE_DIR, "bin", "npx")


def ensure_dirs():
    """确保所有目录存在"""
    for d in [CONFIG_DIR, VENV_DIR, NODE_DIR, MCP_DIR, CONFIG_SUBDIR, HISTORY_DIR]:
        os.makedirs(d, exist_ok=True)


# 驱动映射
DRIVER_MAP = {
    "openai": "openai",
    "zhipuai": "zhipuai", 
    "groq": "groq",
    "anthropic": "anthropic",
    "dashscope": "dashscope"
}

# 驱动编号映射（用于交互式选择）
LIBRARY_DRIVERS = {"1": "openai", "2": "zhipuai", "3": "groq", "4": "dashscope", "5": "anthropic"}

# 能力关键词映射
CAPABILITY_KEYWORDS = {
    "database": ["postgres", "mysql", "sqlite", "mongodb", "database", "sql", "query", "redis"],
    "web_browser": ["puppeteer", "playwright", "browser", "selenium", "web", "scrape", "chrome"],
    "search": ["search", "brave", "google", "bing", "web-search", "fetch", "tavily"],
    "file_system": ["filesystem", "file", "directory", "path", "fs", "fileserver"],
    "git": ["git", "github", "gitlab", "repository", "version", "repo"],
    "memory": ["memory", "knowledge", "graph", "remember", "store", "vector"],
    "ai_ml": ["thinking", "reasoning", "chain", "llm", "model", "embedding", "semantic"],
    "cloud": ["aws", "azure", "gcp", "s3", "cloud", "storage", "bucket"],
    "communication": ["slack", "discord", "email", "telegram", "notify", "message"],
    "data": ["csv", "excel", "json", "xml", "parse", "transform", "spreadsheet"],
    "image": ["image", "vision", "screenshot", "ocr", "visual", "picture"],
    "time": ["calendar", "time", "schedule", "date", "reminder", "clock"],
    "command": ["shell", "terminal", "command", "exec", "run", "process"],
}

# 预定义的可用插件
BUILTIN_PLUGINS = {
    "puppeteer": {
        "name": "puppeteer",
        "npm_package": "@modelcontextprotocol/server-puppeteer",
        "description": "浏览器自动化",
        "capabilities": ["web_browser", "image"],
        "install_cmd": "npx",
        "install_args": ["-y", "@modelcontextprotocol/server-puppeteer"],
        "verified": True,
    },
    "playwright": {
        "name": "playwright",
        "npm_package": "@playwright/mcp",
        "description": "Playwright浏览器自动化",
        "capabilities": ["web_browser", "image"],
        "install_cmd": "npx",
        "install_args": ["-y", "@playwright/mcp"],
        "verified": True,
    },
    "github": {
        "name": "github",
        "npm_package": "@modelcontextprotocol/server-github",
        "description": "GitHub API集成",
        "capabilities": ["git", "cloud"],
        "install_cmd": "npx",
        "install_args": ["-y", "@modelcontextprotocol/server-github"],
        "verified": True,
        "required_env": ["GITHUB_TOKEN"],
    },
    "postgres": {
        "name": "postgres",
        "npm_package": "@modelcontextprotocol/server-postgres",
        "description": "PostgreSQL数据库",
        "capabilities": ["database"],
        "install_cmd": "npx",
        "install_args": ["-y", "@modelcontextprotocol/server-postgres"],
        "verified": True,
        "required_env": ["POSTGRES_CONNECTION_STRING"],
    },
    "sqlite": {
        "name": "sqlite",
        "npm_package": "mcp-server-sqlite",
        "description": "SQLite数据库",
        "capabilities": ["database"],
        "install_cmd": "npx",
        "install_args": ["-y", "mcp-server-sqlite"],
        "verified": True,
    },
    "memory": {
        "name": "memory",
        "npm_package": "@modelcontextprotocol/server-memory",
        "description": "知识图谱存储",
        "capabilities": ["memory"],
        "install_cmd": "npx",
        "install_args": ["-y", "@modelcontextprotocol/server-memory"],
        "verified": True,
    },
    "thinking": {
        "name": "thinking",
        "npm_package": "@modelcontextprotocol/server-sequential-thinking",
        "description": "思维链推理",
        "capabilities": ["ai_ml"],
        "install_cmd": "npx",
        "install_args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        "verified": True,
    },
    "brave-search": {
        "name": "brave-search",
        "npm_package": "@modelcontextprotocol/server-brave-search",
        "description": "Brave搜索",
        "capabilities": ["search"],
        "install_cmd": "npx",
        "install_args": ["-y", "@modelcontextprotocol/server-brave-search"],
        "verified": True,
        "required_env": ["BRAVE_API_KEY"],
    },
    "filesystem": {
        "name": "filesystem",
        "npm_package": "@modelcontextprotocol/server-filesystem",
        "description": "文件系统操作",
        "capabilities": ["file_system"],
        "install_cmd": "npx",
        "install_args": ["-y", "@modelcontextprotocol/server-filesystem"],
        "verified": True,
    },
    "slack": {
        "name": "slack",
        "npm_package": "@modelcontextprotocol/server-slack",
        "description": "Slack消息",
        "capabilities": ["communication"],
        "install_cmd": "npx",
        "install_args": ["-y", "@modelcontextprotocol/server-slack"],
        "verified": True,
        "required_env": ["SLACK_BOT_TOKEN"],
    },
}
