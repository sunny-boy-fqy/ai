"""
AI CLI 终端UI工具
"""

import os
from .constants import VERSION


class UI:
    """终端UI工具类"""
    
    # 颜色代码
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'
    
    @classmethod
    def banner(cls):
        """显示Banner"""
        print(f"{cls.BOLD}{cls.CYAN}")
        print("   ┌─────────────────────────────┐")
        print(f"   │      🤖 AI CLI {VERSION}       │")
        print("   └─────────────────────────────┘")
        print(f"{cls.END}")
    
    @classmethod
    def info(cls, msg: str):
        """信息提示"""
        print(f"{cls.BLUE}●{cls.END} {msg}")
    
    @classmethod
    def success(cls, msg: str):
        """成功提示"""
        print(f"{cls.GREEN}✓{cls.END} {msg}")
    
    @classmethod
    def warn(cls, msg: str):
        """警告提示"""
        print(f"{cls.YELLOW}⚠{cls.END} {msg}")
    
    @classmethod
    def error(cls, msg: str):
        """错误提示"""
        print(f"{cls.RED}✗{cls.END} {msg}")
    
    @classmethod
    def section(cls, title: str):
        """分节标题"""
        print(f"\n{cls.BOLD}{cls.YELLOW}▶ {title}{cls.END}")
    
    @classmethod
    def item(cls, key: str, value: str = "", indent: int = 2):
        """列表项"""
        space = " " * indent
        if value:
            print(f"{space}{cls.GREEN}{key}{cls.END} {cls.DIM}{value}{cls.END}")
        else:
            print(f"{space}{cls.CYAN}{key}{cls.END}")
    
    @classmethod
    def help_item(cls, cmd: str, desc: str):
        """帮助项"""
        print(f"  {cls.GREEN}{cmd:<18}{cls.END} {cls.DIM}{desc}{cls.END}")
    
    @classmethod
    def show_help(cls):
        """显示帮助信息"""
        cls.banner()
        print(f"{cls.BOLD}用法:{cls.END} ai <命令> [参数]")
        print()
        print(f"{cls.BOLD}对话:{cls.END}")
        cls.help_item("ask <问题>", "即时问答")
        cls.help_item("chat", "对话模式")
        cls.help_item("history [load|del]", "历史记录")
        print()
        print(f"{cls.BOLD}配置:{cls.END}")
        cls.help_item("new <名称>", "新建供应商")
        cls.help_item("use <名称>", "切换供应商")
        cls.help_item("model [名称]", "切换模型")
        cls.help_item("list", "列出配置")
        cls.help_item("del <类型> <目标>", "删除配置")
        print()
        print(f"{cls.BOLD}插件:{cls.END}")
        cls.help_item("search <词>", "搜索插件")
        cls.help_item("install <名>", "安装插件")
        cls.help_item("plugin", "已装插件")
        print()
        print(f"{cls.BOLD}任务:{cls.END}")
        cls.help_item("task add <类型> <命令>", "添加任务")
        cls.help_item("task list", "任务列表")
        cls.help_item("task del <ID>", "删除任务")
        cls.help_item("task run <ID>", "执行任务")
        cls.help_item("task start|stop", "守护进程")
        print()
        print(f"{cls.BOLD}系统:{cls.END}")
        cls.help_item("sync <仓库>", "同步配置")
        cls.help_item("update [仓库]", "更新程序")
        cls.help_item("status", "当前状态")
        cls.help_item("version", "版本信息")
    
    @classmethod
    def confirm(cls, msg: str, default: bool = False) -> bool:
        """确认提示"""
        hint = "[Y/n]" if default else "[y/N]"
        try:
            inp = input(f"{msg} {hint}: ").strip().lower()
            if not inp:
                return default
            return inp in ['y', 'yes', '是']
        except:
            return default
    
    @classmethod
    def input(cls, msg: str, default: str = "") -> str:
        """输入提示"""
        try:
            hint = f" [{default}]" if default else ""
            inp = input(f"{msg}{hint}: ").strip()
            return inp if inp else default
        except:
            return default
    
    @classmethod
    def select(cls, msg: str, options: list) -> int:
        """选择提示，返回索引，-1表示取消"""
        print(f"{msg}:")
        for i, opt in enumerate(options):
            print(f"  {cls.GREEN}{i+1}.{cls.END} {opt}")
        try:
            inp = input("选择编号: ").strip()
            if inp.isdigit():
                idx = int(inp) - 1
                if 0 <= idx < len(options):
                    return idx
        except:
            pass
        return -1
