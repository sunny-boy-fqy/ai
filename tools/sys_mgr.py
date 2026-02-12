import os, subprocess
from .constants import BASE_DIR, IS_WINDOWS
from .ui import UI

class SystemManager:
    @staticmethod
    def upgrade(version=None):
        v_args = [version] if version else []
        script_ext = "ps1" if IS_WINDOWS else "sh"
        script = os.path.join(BASE_DIR, f"install.{script_ext}")
        if not os.path.exists(script): return UI.error(f"找不到安装脚本: {script}")
        try:
            UI.info("正在启动升级流程...")
            if IS_WINDOWS:
                subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", f'"{script}"', "--upgrade"] + v_args, check=True)
            else:
                subprocess.run(["bash", script, "--upgrade"] + v_args, check=True)
        except Exception as e: UI.error(f"升级失败: {e}")

    @staticmethod
    def uninstall():
        UI.warn("警告：此操作将彻底删除 AI CLI、所有配置及私有运行环境。")
        if input("确定要彻底卸载吗？(y/N): ").lower() != 'y': return
        script_ext = "ps1" if IS_WINDOWS else "sh"
        script = os.path.join(BASE_DIR, f"uninstall.{script_ext}")
        if not os.path.exists(script): return UI.error(f"找不到卸载脚本: {script}")
        try:
            if IS_WINDOWS:
                subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", f'"{script}"'], check=True)
            else:
                subprocess.run(["bash", script], check=True)
        except Exception as e: UI.error(f"卸载执行失败: {e}")
