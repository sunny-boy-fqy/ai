import os, json, shutil, re
from .constants import CONFIG_PATH, CONFIG_DIR, WORKSPACE_CONFIG, LIBRARY_DRIVERS
from .ui import UI

class ConfigManager:
    @staticmethod
    def load_config():
        if not os.path.exists(CONFIG_PATH):
            return {"current_provider": "", "provider_settings": {}, "base_urls": {}}
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                c = json.load(f)
                c.setdefault("provider_settings", {})
                c.setdefault("base_urls", {})
                return c
        except:
            return {"current_provider": "", "provider_settings": {}, "base_urls": {}}

    @staticmethod
    def save_config(cfg):
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)

    @staticmethod
    def get_current_workspace():
        if os.path.exists(WORKSPACE_CONFIG):
            try:
                w = open(WORKSPACE_CONFIG, 'r', encoding='utf-8').read().strip()
                if os.path.isdir(w): return w
            except: pass
        return os.getcwd()

    @classmethod
    def set_workspace(cls, path):
        abs_p = os.path.abspath(path)
        if not os.path.isdir(abs_p):
            UI.error(f"目录不存在: {abs_p}")
            return
        with open(WORKSPACE_CONFIG, 'w', encoding='utf-8') as f:
            f.write(abs_p)
        UI.success(f"工作区已设为: {abs_p}")

    @classmethod
    def get_contextual_config(cls):
        g = cls.load_config()
        ws = cls.get_current_workspace()
        ctx = g.copy()
        ctx["is_local"], ctx["workspace"] = False, ws
        local_cfg_path = os.path.join(ws, ".ai-config.json")
        if os.path.exists(local_cfg_path):
            try:
                l = json.load(open(local_cfg_path, 'r'))
                if "provider" in l: ctx["current_provider"], ctx["is_local"] = l["provider"], True
                if "model" in l and ctx["current_provider"]:
                    ctx["provider_settings"].setdefault(ctx["current_provider"], {})["current_model"] = l["model"]
                    ctx["is_local"] = True
            except: pass
        return ctx

    @classmethod
    def get_provider_dirs(cls):
        if not os.path.exists(CONFIG_DIR): return []
        return sorted([d for d in os.listdir(CONFIG_DIR) if os.path.isdir(os.path.join(CONFIG_DIR, d)) and d not in ["python_venv", ".git", "mcp_servers", "node"]])

    @classmethod
    def show_list(cls):
        cfg = cls.load_config()
        ps = cls.get_provider_dirs()
        UI.section("AI 供应商详细列表")
        if not ps:
            UI.warn("尚未配置任何供应商。")
            return
        curr = cfg.get("current_provider")
        for p in ps:
            s = cfg["provider_settings"].get(p, {})
            star = "⭐ " if p == curr else "  "
            UI.menu_item(star + p, s.get('driver', 'openai'), f"模型: {s.get('current_model', '未设')} | URL: {cfg['base_urls'].get(p, '默认')}")

    @classmethod
    def setup_new_api(cls):
        cfg = cls.load_config()
        ps = cls.get_provider_dirs()
        UI.section("配置供应商与 API")
        print("1. [追加 API Key] | 2. [新增/修改供应商]")
        mode = input("请选择操作编号: ").strip()
        
        p_name, drv, e_url, e_m = "", "openai", None, "gpt-3.5-turbo"
        if mode == "1":
            if not ps: return UI.error("无现有供应商")
            for i, p in enumerate(ps): print(f"  {i+1}. {p}")
            try:
                idx = int(input("\n请选择供应商编号: "))
                p_name = ps[idx-1]
                s = cfg["provider_settings"].get(p_name, {})
                drv = s.get("driver", "openai")
                e_url = cfg["base_urls"].get(p_name)
                e_m = s.get("current_model", "gpt-3.5-turbo")
            except: return
        else:
            p_name = input("请输入供应商名称: ").strip()
            if not p_name: return
            print("请选择驱动类型:")
            for k, v in LIBRARY_DRIVERS.items(): print(f"  {k}. {v}")
            drv = LIBRARY_DRIVERS.get(input("编号 (默认 1): ").strip() or "1", "openai")

        key = input("请输入 API Key: ").strip()
        if not key: return
        url = input(f"请输入 Base URL (回车保持现有: {e_url}): ").strip() or e_url
        mod = input(f"请输入默认模型 (回车保持现有: {e_m}): ").strip() or e_m
        
        p_dir = os.path.join(CONFIG_DIR, p_name)
        os.makedirs(p_dir, exist_ok=True)
        n = len([f for f in os.listdir(p_dir) if f.startswith("api")]) + 1
        with open(os.path.join(p_dir, f"api_{n}"), 'w') as f: f.write(key)
        
        cfg["provider_settings"][p_name] = {"driver": drv, "current_model": mod, "model_history": [mod]}
        if url: cfg["base_urls"][p_name] = url
        if not cfg.get("current_provider"): cfg["current_provider"] = p_name
        cls.save_config(cfg)
        UI.success("配置已保存")

    @classmethod
    def delete_config(cls):
        cfg = cls.load_config()
        ps = cls.get_provider_dirs()
        UI.section("删除配置")
        if not ps: return UI.warn("无现有配置。")
        for i, p in enumerate(ps): print(f"  {i+1}. {p}")
        try:
            p_idx = int(input("\n请选择供应商编号: ")) - 1
            p_name = ps[p_idx]
            print(f"供应商: {p_name}")
            print("1. [删除整个供应商] | 2. [删除特定的 Key]")
            mode = input("请选择操作: ").strip()
            p_dir = os.path.join(CONFIG_DIR, p_name)
            if mode == "1":
                if input(f"确定删除 {p_name} 及其所有 Key？(y/N): ").lower() == 'y':
                    shutil.rmtree(p_dir)
                    if cfg.get("current_provider") == p_name: cfg["current_provider"] = ""
                    cfg["provider_settings"].pop(p_name, None)
                    cfg["base_urls"].pop(p_name, None)
                    cls.save_config(cfg)
                    UI.success(f"已移除供应商 {p_name}")
            elif mode == "2":
                keys = sorted([f for f in os.listdir(p_dir) if f.startswith("api")])
                for i, k in enumerate(keys): print(f"  {i+1}. {k}")
                k_idx = int(input("请选择要删除的 Key 编号: ")) - 1
                target_k = keys[k_idx]
                os.remove(os.path.join(p_dir, target_k))
                # 自动补位
                rem = sorted([f for f in os.listdir(p_dir) if f.startswith("api")])
                if rem:
                    itf = int(re.search(r"api_(\d+)", target_k).group(1))
                    last_k = rem[-1]
                    last_idx = int(re.search(r"api_(\d+)", last_k).group(1))
                    if last_idx > itf:
                        os.rename(os.path.join(p_dir, last_k), os.path.join(p_dir, f"api_{itf}"))
                else: shutil.rmtree(p_dir)
                UI.success("Key 已删除并自动重排。")
        except: pass

    @classmethod
    def manage_model(cls):
        ctx = cls.get_contextual_config()
        p = ctx.get("current_provider")
        if not p: return UI.error("尚未配置供应商。")
        s = ctx["provider_settings"].get(p, {})
        hist = s.get("model_history", [])
        UI.section(f"管理供应商模型: {p}")
        print(f"当前模型: {UI.BOLD}{s.get('current_model')}{UI.END}")
        print(f"历史记录: {', '.join(hist)}")
        choice = input("\nn. [录入新模型] | 输入编号切换 | 直接回车取消: ").strip().lower()
        g = cls.load_config()
        if choice == 'n':
            new_m = input("请输入模型名称: ").strip()
            if new_m:
                g["provider_settings"][p]["current_model"] = new_m
                if new_m not in g["provider_settings"][p].get("model_history", []):
                    g["provider_settings"][p].setdefault("model_history", []).append(new_m)
                cls.save_config(g)
                UI.success("模型已更新")
        elif choice.isdigit():
            try:
                idx = int(choice) - 1
                g["provider_settings"][p]["current_model"] = hist[idx]
                cls.save_config(g)
                UI.success(f"已切换至模型: {hist[idx]}")
            except: pass
