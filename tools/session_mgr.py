import os, json
from datetime import datetime
from .constants import SESSION_DIR
from .ui import UI

class SessionManager:
    @staticmethod
    def list_sessions():
        if not os.path.exists(SESSION_DIR): os.makedirs(SESSION_DIR, exist_ok=True)
        files = sorted([f for f in os.listdir(SESSION_DIR) if f.endswith(".json")], reverse=True)
        UI.section("最近对话历史")
        UI.menu_item("0", "➕ 启动全新对话")
        data_list = []
        for i, f in enumerate(files[:20]):
            try:
                with open(os.path.join(SESSION_DIR, f), 'r', encoding='utf-8') as file:
                    d = json.load(file)
                    UI.menu_item(str(i+1), f"[{f[2:10]}] {d.get('title', '无标题')}")
                    data_list.append((f, d))
            except: pass
        return data_list

    @staticmethod
    def save_session(session_file, messages):
        if not messages: return
        # Safely extract title from the first user message if available
        title = "新会话"
        for m in messages:
            if m["role"] == "user":
                title = m["content"][:50].replace("\n", " ")
                break
        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump({"title": title, "messages": messages}, f, indent=4, ensure_ascii=False)
        except Exception as e:
            UI.error(f"保存失败: {e}")

    @staticmethod
    def delete_session(filename):
        try:
            p = os.path.join(SESSION_DIR, filename)
            if os.path.exists(p):
                os.remove(p)
                UI.success("记录已删除")
                return True
        except: pass
        return False
