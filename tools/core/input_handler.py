"""
AI CLI 输入处理器
支持多行输入和特殊功能
"""

import sys
import os
from typing import Optional, List


class InputHandler:
    """高级输入处理器"""
    
    def __init__(self, prompt: str = "", allow_multiline: bool = True):
        """
        初始化输入处理器
        
        Args:
            prompt: 提示符
            allow_multiline: 是否允许多行输入
        """
        self.prompt = prompt
        self.allow_multiline = allow_multiline
        self.history: List[str] = []
    
    def get_input(self) -> str:
        """
        获取用户输入，支持多行
        
        支持的多行输入方式：
        1. 以反斜杠结尾 - 继续输入下一行
        2. 输入三引号或三个反引号开始多行块，再次输入结束
        
        Returns:
            用户输入的完整文本
        """
        lines = []
        in_multiline_block = False
        multiline_delimiter = None
        
        while True:
            try:
                # 显示提示符
                if lines:
                    # 续行提示
                    display_prompt = "..." if in_multiline_block else "   "
                else:
                    display_prompt = self.prompt
                
                # 获取输入
                line = input(f"{display_prompt} ")
                
                # 检查多行块标记
                if self.allow_multiline:
                    # 开始多行块
                    if not in_multiline_block and line.strip() in ['```', '"""', "'''"]:
                        in_multiline_block = True
                        multiline_delimiter = line.strip()
                        lines.append(line)
                        continue
                    
                    # 结束多行块
                    if in_multiline_block and line.strip() == multiline_delimiter:
                        in_multiline_block = False
                        lines.append(line)
                        continue
                    
                    # 在多行块中
                    if in_multiline_block:
                        lines.append(line)
                        continue
                    
                    # 检查是否要继续输入（以反斜杠结尾）
                    if line.rstrip().endswith('\\'):
                        # 去掉续行符，继续输入
                        lines.append(line.rstrip()[:-1])
                        continue
                    
                    # 检查是否是命令（单行命令直接执行）
                    if line.strip().lower() in ['exit', 'quit', 'status', 'clear']:
                        return line.strip()
                
                # 普通输入
                lines.append(line)
                break
                
            except EOFError:
                # Ctrl+D
                return ""
            except KeyboardInterrupt:
                # Ctrl+C
                print("\n")
                return ""
        
        result = '\n'.join(lines)
        
        # 保存到历史
        if result.strip():
            self.history.append(result)
        
        return result
    
    def get_multiline_input(
        self,
        start_marker: str = "```",
        end_marker: Optional[str] = None
    ) -> str:
        """
        获取多行输入（使用标记包围）
        
        Args:
            start_marker: 开始标记
            end_marker: 结束标记（默认与开始标记相同）
            
        Returns:
            多行文本
        """
        if end_marker is None:
            end_marker = start_marker
        
        print(f"输入 {start_marker} 开始，{end_marker} 结束")
        
        lines = []
        in_block = False
        
        while True:
            try:
                line = input()
                
                if line.strip() == start_marker and not in_block:
                    in_block = True
                    continue
                
                if line.strip() == end_marker and in_block:
                    break
                
                if in_block:
                    lines.append(line)
                    
            except (EOFError, KeyboardInterrupt):
                break
        
        return '\n'.join(lines)
    
    def confirm(self, message: str) -> bool:
        """
        确认对话框
        
        Args:
            message: 确认消息
            
        Returns:
            用户是否确认
        """
        try:
            response = input(f"{message} [y/N]: ").strip().lower()
            return response in ['y', 'yes', '是', '确定']
        except:
            return False


def get_user_input(prompt: str = "", allow_multiline: bool = True) -> str:
    """
    获取用户输入的便捷函数
    
    Args:
        prompt: 提示符
        allow_multiline: 是否允许多行
        
    Returns:
        用户输入
    """
    handler = InputHandler(prompt, allow_multiline)
    return handler.get_input()


def get_multiline_input() -> str:
    """
    获取多行输入的便捷函数
    用户输入三引号开始，再输入三引号结束
    
    Returns:
        多行文本
    """
    handler = InputHandler("")
    return handler.get_multiline_input()
