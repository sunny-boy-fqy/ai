import os, subprocess, tempfile, stat, shutil, json
from .constants import CONFIG_DIR, IS_WINDOWS, BASE_DIR
from .config_mgr import ConfigManager
from .ui import UI

class SyncManager:
    @staticmethod
    def git_sync(repo_url, mode="download"):
        if not repo_url.startswith("git@"): return UI.error("仅支持 SSH 协议 (git@...)")
        
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
        
        if IS_WINDOWS:
            ssh_dir = os.path.join(os.environ.get("USERPROFILE",""), ".ssh")
            for k in ["id_rsa", "id_ed25519", "id_ecdsa"]:
                p = os.path.join(ssh_dir, k)
                if os.path.exists(p): 
                    env["GIT_SSH_COMMAND"] += f' -i "{p}"'
                    break

        def rmr(f, p, _): os.chmod(p, stat.S_IWRITE); f(p)
        tmp = tempfile.mkdtemp()
        
        try:
            UI.info(f"正在同步远程仓库...")
            subprocess.run(["git", "clone", "--depth", "1", repo_url, tmp], env=env, check=True)
            
            if mode == "download":
                if input("是否合并远程配置？(y/N): ").lower() != 'y': return
                n_p = os.path.join(tmp, "config.json")
                if os.path.exists(n_p):
                    try:
                        n_c = json.load(open(n_p, 'r'))
                        o_c = ConfigManager.load_config()
                        for p, s in n_c.get("provider_settings", {}).items():
                            if p not in o_c["provider_settings"]: o_c["provider_settings"][p] = s
                            else: o_c["provider_settings"][p]["model_history"] = list(set(o_c["provider_settings"][p].get("model_history", []) + s.get("model_history", [])))
                        o_c["base_urls"].update(n_c.get("base_urls", {}))
                        ConfigManager.save_config(o_c)
                    except: pass
                
                for p in os.listdir(tmp):
                    src = os.path.join(tmp, p)
                    if not os.path.isdir(src) or p in ["node", "python_venv", ".git", "mcp_servers"]: continue
                    dst = os.path.join(CONFIG_DIR, p); os.makedirs(dst, exist_ok=True)
                    for k in os.listdir(src):
                        try:
                            val = open(os.path.join(src, k), 'r').read().strip()
                            if not any(open(os.path.join(dst, ex), 'r').read().strip() == val for ex in os.listdir(dst) if ex.startswith("api")):
                                n = len([f for f in os.listdir(dst) if f.startswith("api")]) + 1
                                open(os.path.join(dst, f"api_{n}"), 'w').write(val)
                        except: pass
                UI.success("同步合并完成")
            else: # Upload
                lc = ConfigManager.load_config()
                json.dump(lc, open(os.path.join(tmp, "config.json"), 'w'), indent=4, ensure_ascii=False)
                for p in ConfigManager.get_provider_dirs():
                    src, dst = os.path.join(CONFIG_DIR, p), os.path.join(tmp, p); os.makedirs(dst, exist_ok=True)
                    for k in os.listdir(src):
                        if k.startswith("api"): shutil.copy2(os.path.join(src, k), dst)
                os.chdir(tmp)
                subprocess.run(["git", "add", "."], env=env)
                subprocess.run(["git", "commit", "-m", "CLI Sync"], env=env)
                subprocess.run(["git", "push"], env=env)
                UI.success("本地配置已叠加到远程仓库")
        except Exception as e: UI.error(f"失败: {e}")
        finally: os.chdir(BASE_DIR); shutil.rmtree(tmp, onexc=rmr)
