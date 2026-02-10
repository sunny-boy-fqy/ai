#!/usr/bin/env python3
import sys
import os
import json
import subprocess
import shutil

# Read base directory from config file
CONFIG_DIR = os.path.expanduser("~/.config/ai")
if not os.path.exists(os.path.join(CONFIG_DIR, 'base_path.config')):
    # Fallback or initialization logic if needed
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
else:
    with open(os.path.join(CONFIG_DIR, 'base_path.config'), 'r') as f:
        BASE_DIR = f.read().strip()

CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
VENV_PIP = os.path.join(CONFIG_DIR, "python_venv/bin/pip")

# 预设的底层库驱动
LIBRARY_DRIVERS = {
    "1": "openai",
    "2": "zhipuai",
    "3": "groq",
    "4": "dashscope",
    "5": "anthropic"
}

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {
            "current_provider": "", 
            "provider_settings": {}, 
            "base_urls": {}
        }
    try:
        with open(CONFIG_PATH, "r", encoding='utf-8') as f:
            cfg = json.load(f)
            if "provider_settings" not in cfg: cfg["provider_settings"] = {}
            if "base_urls" not in cfg: cfg["base_urls"] = {}
            return cfg
    except:
        return {"current_provider": "", "provider_settings": {}, "base_urls": {}}

def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding='utf-8') as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

def get_provider_dirs():
    if not os.path.exists(CONFIG_DIR): return []
    return sorted([d for d in os.listdir(CONFIG_DIR) if os.path.isdir(os.path.join(CONFIG_DIR, d)) and d not in ["python_venv", ".git"]])

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
        # 极简调用测试
        c.chat.completions.create(
            model=model, 
            messages=[{"role": "user", "content": "hi"}], 
            max_tokens=1
        )
        print("✅ 验证成功！该 API 和模型可用。")
        return True
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def setup_new_api():
    cfg = load_config()
    print("\n=== 🛠️  AI 供应商 & API 管理 ===")
    providers = get_provider_dirs()
    print("你想执行什么操作？")
    print("1. [追加] 为现有的供应商添加更多 API Key")
    print("2. [新增] 配置一个全新的供应商 (支持不同厂商共用同一个驱动库)")
    mode = input("请选择 (1/2): ").strip()
    provider_name = ""
    driver_lib = ""
    if mode == "1":
        if not providers:
            print("❌ 当前没有任何已配置的供应商，请先选择 '2' 新增。")
            return
        print("\n请选择供应商：")
        for i, p in enumerate(providers):
            print(f"{i+1}. {p}")
        idx = input("输入编号: ").strip()
        try:
            provider_name = providers[int(idx)-1]
            driver_lib = cfg["provider_settings"].get(provider_name, {}).get("driver", "openai")
        except: 
            print("无效的选择。")
            return
    else:
        print("\n--- 新增供应商配置 ---")
        provider_name = input("请输入此供应商的【名称】(例如 deepseek, work_ai): ").strip()
        if not provider_name: return
        print("\n请选择此供应商使用的【底层驱动库】：")
        print("1. openai (通用)")
        print("2. zhipuai")
        print("3. groq")
        print("4. dashscope")
        print("5. anthropic")
        lib_idx = input("请选择编号 (默认 1): ").strip() or "1"
        driver_lib = LIBRARY_DRIVERS.get(lib_idx, "openai")
    
    key = input(f"请输入【{provider_name}】的 API Key: ").strip()
    if not key: return
    
    url = None
    if mode != "1":
        url = input(f"请输入【{provider_name}】的 Base URL (可选): ").strip() or None
    
    # 获取用于测试的模型名
    test_m = input("请输入一个该平台可用的模型名用于验证 (如 gpt-4o, glm-4-flash): ").strip()
    if not test_m:
        print("❌ 必须输入测试模型名以后验证。")
        return
    
    # 验证
    if not test_connection(driver_lib, key, url, test_m):
        cont = input("⚠️ 验证失败，是否仍要保存配置？(y/N): ").strip().lower()
        if cont != 'y': return
    
    # 准备目录
    prov_dir = os.path.join(CONFIG_DIR, provider_name)
    os.makedirs(prov_dir, exist_ok=True)
    existing_keys = [f for f in os.listdir(prov_dir) if f.startswith("api")]
    count = len(existing_keys)
    fname = "api" if count == 0 else f"api_{count + 1}"
    with open(os.path.join(prov_dir, fname), "w") as f:
        f.write(key)
    
    # 更新配置
    if provider_name not in cfg["provider_settings"]:
        cfg["provider_settings"][provider_name] = {
            "driver": driver_lib,
            "current_model": test_m,
            "model_history": [test_m]
        }
    else:
        if test_m not in cfg["provider_settings"][provider_name]["model_history"]:
            cfg["provider_settings"][provider_name]["model_history"].append(test_m)
    
    if url: 
        cfg["base_urls"][provider_name] = url
    if not cfg.get("current_provider"):
        cfg["current_provider"] = provider_name
    
    save_config(cfg)
    print(f"\n✅ 成功！Key 已存入: {provider_name}/{fname}")
    # 异步确保库安装
    subprocess.Popen([VENV_PIP, "install", driver_lib], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def manage_model():
    cfg = load_config()
    p = cfg.get("current_provider")
    if not p: return print("请先运行 'ai new'。")
    settings = cfg["provider_settings"].get(p, {})
    current_m = settings.get("current_model", "未设置")
    history = settings.get("model_history", [])
    print(f"\n当前供应商: {p} | 当前模型: {current_m}")
    print("\n--- 模型选项 ---")
    if history:
        for i, h_m in enumerate(history):
            print(f"{i+1}. {h_m}")
    print("\nn. [输入并使用新模型]")
    print("d. [删除选中的历史模型]")
    choice = input("\n请选择操作 (1-N / n / d): ").strip().lower()
    if choice == 'n':
        new_m = input("直接输入模型名称: ").strip()
        if not new_m: return
        p_dir = os.path.join(CONFIG_DIR, p)
        keys = [f for f in os.listdir(p_dir) if f.startswith("api")]
        with open(os.path.join(p_dir, keys[0]), "r") as f: key_val = f.read().strip()
        if test_connection(settings.get("driver"), key_val, cfg["base_urls"].get(p), new_m):
            settings["current_model"] = new_m
            if new_m not in history: history.append(new_m)
            cfg["provider_settings"][p] = settings
            save_config(cfg)
            print(f"✅ 模型已成功切换至: {new_m}")
    elif choice == 'd':
        if not history: return
        idx = input("请输入要从历史中删除的模型编号: ").strip()
        try:
            removed = history.pop(int(idx)-1)
            settings["model_history"] = history
            cfg["provider_settings"][p] = settings
            save_config(cfg)
            print(f"✅ 已删除记录: {removed}")
        except: print("❌ 无效编号")
    elif choice.isdigit():
        try:
            target = history[int(choice)-1]
            settings["current_model"] = target
            cfg["provider_settings"][p] = settings
            save_config(cfg)
            print(f"✅ 已切换至: {target}")
        except: print("❌ 无效编号")

def delete_provider():
    cfg = load_config()
    ps = get_provider_dirs()
    if not ps: return print("没有可删除的供应商。")
    print("\n--- ⚠️ 删除供应商 ---")
    for i, p in enumerate(ps):
        print(f"{i+1}. {p}")
    idx = input("请选择要彻底删除的供应商编号 (或 q 退出): ").strip()
    if idx.lower() == 'q': return
    try:
        p_name = ps[int(idx)-1]
        confirm = input(f"此操作将永久删除文件夹 {p_name} 及其所有 Key，确定吗？(y/N): ").strip().lower()
        if confirm == 'y':
            shutil.rmtree(os.path.join(CONFIG_DIR, p_name))
            if p_name in cfg["provider_settings"]: del cfg["provider_settings"][p_name]
            if p_name in cfg["base_urls"]: del cfg["base_urls"][p_name]
            if cfg.get("current_provider") == p_name:
                cfg["current_provider"] = ""
            save_config(cfg)
            print(f"✅ 供应商 【{p_name}】 已被抹除。")
    except:
        print("❌ 操作取消或无效编号")

def show_status():
    cfg = load_config()
    cp = cfg.get("current_provider", "未设置")
    sett = cfg["provider_settings"].get(cp, {})
    cm = sett.get("current_model", "未设置")
    cu = cfg["base_urls"].get(cp, "官方默认")
    dr = sett.get("driver", "openai")
    print("\n=== 🌍 AI 系统状态面板 ===")
    print(f"📍 当前供应商: {cp} (驱动: {dr})")
    print(f"🤖 当前模型:   {cm}")
    print(f"🔗 接口地址:   {cu}")
    print("\n[供应商资产统计]")
    for p in get_provider_dirs():
        p_dir = os.path.join(CONFIG_DIR, p)
        keys = [f for f in os.listdir(p_dir) if f.startswith("api")]
        star = " ★" if p == cp else ""
        p_sett = cfg["provider_settings"].get(p, {})
        drv = p_sett.get("driver", "未知")
        print(f" - {p} ({drv}){star}: {len(keys)} 个 Key")
    print("\n💡 输入 'ai -h' 查看帮助。")

def show_help():
    print("""
🤖 AI 命令行工具使用手册
================================
1. 【对话】ai [内容]
   使用当前配置直接对话。支持流式打印。
2. 【连续对话】ai chat
   进入交互式对话模式，支持上下文记忆。
3. 【管理配置】ai new
   配置新供应商或追加 Key。包含【可用性验证】步骤。
4. 【管理模型】ai model
   切换模型、添加并验证新模型、或清除历史记录。
5. 【切换供应商】ai switch
   在不同的本地供应商配置之间切换。
6. 【代理设置】ai url
   修改当前供应商的基础访问地址。
7. 【删除平台】ai delete
   永久移除某个供应商及其所有残留数据。
8. 【状态查看】ai status (或直接输入 'ai')
   查看当前使用的平台、模型、URL 以及全量资产统计。

帮助：输入 'ai -h' 显示此页面。
================================
""")

def start_chat():
    cfg = load_config()
    p = cfg.get("current_provider")
    if not p: return print("尚未初始化，请输入 'ai new'")
    sett = cfg["provider_settings"].get(p, {})
    m = sett.get("current_model")
    driver = sett.get("driver", "openai")
    base_url = cfg["base_urls"].get(p)
    p_dir = os.path.join(CONFIG_DIR, p)
    keys = [f for f in os.listdir(p_dir) if f.startswith("api")]
    if not keys: return print("❌ 找不到 Key。")
    with open(os.path.join(p_dir, keys[0]), "r") as f: kv = f.read().strip()

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

    messages = []
    print(f"💬 进入对话模式 [{p} | {m}] (输入 'exit' 或 'quit' 退出，'clear' 清空对话)\n")
    while True:
        try:
            user_input = input("You > ").strip()
            if not user_input: continue
            if user_input.lower() in ["exit", "quit"]: break
            if user_input.lower() == "clear":
                messages = []
                print("✨ 对话记录已清空。\n")
                continue
            
            messages.append({"role": "user", "content": user_input})
            print(f"AI > ", end="", flush=True)
            
            res = c.chat.completions.create(model=m, messages=messages, stream=True)
            full_response = ""
            for chunk in res:
                if hasattr(chunk, 'choices') and chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    print(content, end="", flush=True)
                    full_response += content
            print("\n")
            messages.append({"role": "assistant", "content": full_response})
        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as e:
            print(f"\n❌ 失败: {e}")

def call_ai(args):
    quiet = False
    if args and args[0] in ["-q", "--quiet"]:
        quiet = True
        args = args[1:]
    
    cfg = load_config()
    p = cfg.get("current_provider")
    if not p: return print("尚未初始化，请输入 'ai new'")
    sett = cfg["provider_settings"].get(p, {})
    m = sett.get("current_model")
    driver = sett.get("driver", "openai")
    base_url = cfg["base_urls"].get(p)
    p_dir = os.path.join(CONFIG_DIR, p)
    keys = [f for f in os.listdir(p_dir) if f.startswith("api")]
    if not keys: return print("❌ 找不到 Key。")
    with open(os.path.join(p_dir, keys[0]), "r") as f: kv = f.read().strip()
    prompt = " ".join(args)
    if not quiet:
        print(f"🚀 [{p} | {m}] 响应中...\n")
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
        res = c.chat.completions.create(model=m, messages=[{"role":"user","content":prompt}], stream=True)
        for chunk in res:
            if hasattr(chunk, 'choices') and chunk.choices and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        if not quiet:
            print("\n")
    except Exception as e: 
        if not quiet: print(f"\n❌ 失败: {e}")
        else: pass # Or handle differently for quiet mode

def main():
    if len(sys.argv) < 2:
        show_status()
        return
    cmd = sys.argv[1].lower()
    if cmd in ["-h", "--help"]: show_help()
    elif cmd == "new": setup_new_api()
    elif cmd == "chat": start_chat()
    elif cmd == "url": 
        cfg = load_config()
        p = cfg.get("current_provider")
        if not p: return
        print(f"当前 URL: {cfg['base_urls'].get(p, '默认')}")
        url = input("输入新 Base URL (输入 clear 清理): ").strip()
        if url.lower() == 'clear':
            if p in cfg["base_urls"]: del cfg["base_urls"][p]
        elif url: cfg["base_urls"][p] = url
        save_config(cfg)
        print("✅ URL 已更新。")
    elif cmd == "model": manage_model()
    elif cmd == "status": show_status()
    elif cmd == "delete": delete_provider()
    elif cmd == "switch":
        cfg = load_config()
        ps = get_provider_dirs()
        for i, p in enumerate(ps): print(f"{i+1}. {p}")
        idx = input("请选择供应商编号: ").strip()
        try:
            cfg["current_provider"] = ps[int(idx)-1]
            save_config(cfg)
            print(f"✅ 已切换供应商至: {cfg['current_provider']}")
        except: pass
    else: call_ai(sys.argv[1:])

if __name__ == "__main__":
    main()