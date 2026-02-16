import os
from .constants import VERSION


class UI:
    """UI 工具类"""
    
    # 颜色常量
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'

    @staticmethod
    def get_version():
        return VERSION

    @classmethod
    def banner(cls):
        v = cls.get_version()
        print(f"{cls.BOLD}{cls.CYAN}")
        print("   ┌──────────────────────────────────────────┐")
        print(f"   │         🤖  AI CLI ASSISTANT {v}        │")
        print("   └──────────────────────────────────────────┘")
        print(f"{cls.END}")

    @classmethod
    def info(cls, msg):
        print(f"{cls.BLUE}[INFO]{cls.END} {msg}")

    @classmethod
    def success(cls, msg):
        print(f"{cls.GREEN}[SUCCESS]{cls.END} {msg}")

    @classmethod
    def warn(cls, msg):
        print(f"{cls.YELLOW}[WARN]{cls.END} {msg}")

    @classmethod
    def error(cls, msg):
        print(f"{cls.RED}[ERROR]{cls.END} {msg}")

    @classmethod
    def section(cls, title):
        print(f"\n{cls.BOLD}{cls.YELLOW}=== {title} ==={cls.END}")

    @classmethod
    def menu_item(cls, idx, label, desc=""):
        line = f"  {cls.GREEN}{idx}.{cls.END} {cls.BOLD}{label}{cls.END}"
        if desc:
            line += f" - {cls.CYAN}{desc}{cls.END}"
        print(line)

    @classmethod
    def item(cls, label, value=""):
        """显示项目"""
        if value:
            print(f"  {cls.CYAN}{label}{cls.END} {value}")
        else:
            print(f"  {label}")

    @classmethod
    def input(cls, prompt: str, default: str = "") -> str:
        """获取用户输入"""
        hint = f" [{default}]" if default else ""
        try:
            result = input(f"  {prompt}{hint}: ").strip()
            return result if result else default
        except EOFError:
            return default

    @classmethod
    def confirm(cls, prompt: str, default: bool = False) -> bool:
        """确认对话框"""
        hint = "Y/n" if default else "y/N"
        try:
            result = input(f"  {prompt} [{hint}]: ").strip().lower()
            if not result:
                return default
            return result in ('y', 'yes', '是')
        except EOFError:
            return default

    @classmethod
    def show_help(cls):
        """显示帮助信息"""
        cls.banner()
        print(f"""
{cls.BOLD}用法:{cls.END}
  ai <命令> [参数]

{cls.BOLD}全局参数:{cls.END}
  --debug, -d         启用调试模式（详细日志输出）

{cls.BOLD}Leader-Worker 模式:{cls.END}
  ai init              初始化当前目录(.ai文件夹)
  ai init --auto       使用全局配置自动初始化
  ai work              进入Leader-Worker工作模式(交互式)
  ai work --file <文件> 从文件执行任务(非交互式)
  ai work --task <任务> 直接执行任务(非交互式)
  ai work --debug      启用调试模式
  ai work --resume     恢复上次未完成的任务

{cls.BOLD}对话:{cls.END}
  ai ask <问题>        即时问答
  ai chat              进入对话模式
  ai history           查看历史记录
  ai history load <n>  加载历史对话

{cls.BOLD}供应商:{cls.END}
  ai new [名称]        创建供应商
  ai use [名称]        切换供应商
  ai model [名称]      切换模型
  ai list              列出所有供应商
  ai del provider <名称> 删除供应商
  ai status            显示当前状态

{cls.BOLD}工作区:{cls.END}
  ai workspace         显示工作区
  ai workspace <路径>  添加工作区目录
  ai workspace rm <n>  移除工作区
  ai workspace clear   清空工作区

{cls.BOLD}插件:{cls.END}
  ai search <关键词>   搜索插件
  ai install <名称>    安装插件
  ai plugin            显示已安装插件
  ai del plugin <名称> 卸载插件

{cls.BOLD}任务:{cls.END}
  ai task              列出任务
  ai task add <类型> <命令>  添加任务
  ai task run <ID>     执行任务
  ai task start        启动守护进程
  ai task stop         停止守护进程

{cls.BOLD}其他:{cls.END}
  ai version           显示版本
  ai sync <URL>        从github仓库同步配置(git@github.com:...)
  ai update            更新程序
  ai update <URL>      向github仓库更新配置(git@github.com:...)
  ai help              显示帮助

{cls.BOLD}新增功能 (v0.2.0):{cls.END}
  • API 调用自动重试（失败时最多重试3次）
  • 智能上下文压缩（防止溢出）
  • 任务恢复功能（ai work --resume）
  • 并行任务执行（assign_tasks_parallel 工具）
  • 进度可视化显示
  • 调试模式（--debug）
""")
