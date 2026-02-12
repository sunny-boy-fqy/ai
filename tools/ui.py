import os
from .constants import VERSION_FILE

class UI:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

    @staticmethod
    def get_version():
        if os.path.exists(VERSION_FILE):
            try:
                with open(VERSION_FILE, "r") as f: return f.read().strip()
            except: pass
        return "v1.1"

    @classmethod
    def banner(cls):
        v = cls.get_version()
        print(f"{cls.BOLD}{cls.CYAN}")
        print("   ┌──────────────────────────────────────────┐")
        print(f"   │         🤖  AI CLI ASSISTANT {v}        │")
        print("   └──────────────────────────────────────────┘")
        print(f"{cls.END}")

    @classmethod
    def info(cls, msg): print(f"{cls.BLUE}[INFO]{cls.END} {msg}")
    @classmethod
    def success(cls, msg): print(f"{cls.GREEN}[SUCCESS]{cls.END} {msg}")
    @classmethod
    def warn(cls, msg): print(f"{cls.YELLOW}[WARN]{cls.END} {msg}")
    @classmethod
    def error(cls, msg): print(f"{cls.RED}[ERROR]{cls.END} {msg}")

    @classmethod
    def section(cls, title):
        print(f"\n{cls.BOLD}{cls.YELLOW}=== {title} ==={cls.END}")

    @classmethod
    def menu_item(cls, idx, label, desc=""):
        line = f"  {cls.GREEN}{idx}.{cls.END} {cls.BOLD}{label}{cls.END}"
        if desc: line += f" - {cls.CYAN}{desc}{cls.END}"
        print(line)
