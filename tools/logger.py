"""
AI CLI 日志模块
支持不同日志级别的输出和控制
"""

import os
import sys
from datetime import datetime
from typing import Optional

# 日志级别
DEBUG = 0
INFO = 1
WARN = 2
ERROR = 3
NONE = 4

# 全局日志级别（默认 INFO）
_log_level = INFO
_log_file = None


def set_log_level(level: int):
    """设置日志级别"""
    global _log_level
    _log_level = level


def set_log_file(filepath: str):
    """设置日志文件"""
    global _log_file
    _log_file = filepath
    # 确保目录存在
    if filepath:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)


def get_log_level() -> int:
    """获取当前日志级别"""
    return _log_level


def _write(level: int, prefix: str, msg: str, color: str = ""):
    """写入日志"""
    if level < _log_level:
        return
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    END = "\033[0m"
    
    # 控制台输出
    if level >= INFO:
        print(f"{color}[{prefix}]{END} {msg}")
    else:
        # DEBUG 级别带时间戳
        print(f"{color}[{prefix}]{END} {timestamp} - {msg}")
    
    # 文件输出
    if _log_file:
        try:
            with open(_log_file, 'a', encoding='utf-8') as f:
                level_names = {DEBUG: "DEBUG", INFO: "INFO", WARN: "WARN", ERROR: "ERROR"}
                f.write(f"[{timestamp}] [{level_names.get(level, 'LOG')}] {msg}\n")
        except:
            pass


def debug(msg: str):
    """调试日志"""
    _write(DEBUG, "DEBUG", msg, "\033[90m")  # 灰色


def info(msg: str):
    """信息日志"""
    _write(INFO, "INFO", msg, "\033[94m")  # 蓝色


def warn(msg: str):
    """警告日志"""
    _write(WARN, "WARN", msg, "\033[93m")  # 黄色


def error(msg: str):
    """错误日志"""
    _write(ERROR, "ERROR", msg, "\033[91m")  # 红色


def api(msg: str):
    """API 调用日志（DEBUG 级别）"""
    _write(DEBUG, "API", msg, "\033[96m")  # 青色


def task(msg: str):
    """任务日志"""
    _write(INFO, "TASK", msg, "\033[92m")  # 绿色


class LogContext:
    """日志上下文管理器"""
    
    def __init__(self, name: str, log_file: Optional[str] = None):
        self.name = name
        self.log_file = log_file or os.path.expanduser("~/.config/ai/logs/ai.log")
        self._old_level = _log_level
        self._old_file = _log_file
    
    def __enter__(self):
        set_log_file(self.log_file)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        set_log_file(self._old_file)
        return False
