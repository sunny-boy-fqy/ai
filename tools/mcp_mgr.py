import os, json, sys, asyncio
from .constants import MCP_CONFIG, IS_WINDOWS
from .ui import UI

class MCPManager:
    @staticmethod
    def fetch_mcp_market():
        return {
            "browser": {"cmd": "npx", "args": ["-y", "@modelcontextprotocol/server-puppeteer"], "desc": "浏览器自动化 (Puppeteer)"},
            "git": {"cmd": "npx", "args": ["-y", "@modelcontextprotocol/server-git"], "desc": "Git 本地操作"},
            "github": {"cmd": "npx", "args": ["-y", "@modelcontextprotocol/server-github"], "desc": "GitHub API 集成"},
            "google-maps": {"cmd": "npx", "args": ["-y", "@modelcontextprotocol/server-google-maps"], "desc": "地图与位置服务"},
            "postgres": {"cmd": "npx", "args": ["-y", "@modelcontextprotocol/server-postgres"], "desc": "数据库查询"},
            "memory": {"cmd": "npx", "args": ["-y", "@modelcontextprotocol/server-memory"], "desc": "知识图谱长期记忆"},
            "thinking": {"cmd": "npx", "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"], "desc": "思维链推理增强"}
        }

    @classmethod
    async def search_market(cls, query=""):
        market = cls.fetch_mcp_market()
        results = []
        for name, info in market.items():
            if not query or query.lower() in name or query.lower() in info["desc"].lower():
                results.append(name)
        return results

    @classmethod
    async def install_plugin(cls, name, command=None, args=None):
        market = cls.fetch_mcp_market()
        if not command and name in market:
            item = market[name]
            command, args = item["cmd"], item["args"]
        if not command: return UI.error(f"未知插件: {name}")
        try:
            cfg = json.load(open(MCP_CONFIG, 'r', encoding='utf-8')) if os.path.exists(MCP_CONFIG) else {"servers": {}}
            if IS_WINDOWS and command == "npx": command = "npx.cmd"
            cfg.setdefault("servers", {})[name] = {"command": command, "args": args or []}
            json.dump(cfg, open(MCP_CONFIG, 'w', encoding='utf-8'), indent=4, ensure_ascii=False)
            UI.success(f"插件 '{name}' 已安装。环境已重载。")
            return True
        except Exception as e: return UI.error(f"安装失败: {e}")
