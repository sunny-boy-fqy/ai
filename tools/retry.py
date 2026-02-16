"""
AI CLI 重试机制
提供 API 调用的自动重试功能
"""

import asyncio
import functools
import random
from typing import Callable, Type, Tuple, Optional
from .logger import debug, warn, error


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_backoff: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        exponential_backoff: 是否使用指数退避
        exceptions: 需要重试的异常类型
        on_retry: 重试时的回调函数
        
    Returns:
        装饰后的函数
    """
    def decorator(func):
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt >= max_retries:
                        error(f"重试 {max_retries} 次后仍失败: {e}")
                        raise
                    
                    # 计算延迟
                    if exponential_backoff:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        # 添加随机抖动
                        delay = delay * (0.5 + random.random())
                    else:
                        delay = base_delay
                    
                    warn(f"调用失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                    debug(f"将在 {delay:.1f} 秒后重试...")
                    
                    if on_retry:
                        on_retry(attempt, e, delay)
                    
                    import time
                    time.sleep(delay)
            
            raise last_exception
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt >= max_retries:
                        error(f"重试 {max_retries} 次后仍失败: {e}")
                        raise
                    
                    # 计算延迟
                    if exponential_backoff:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        delay = delay * (0.5 + random.random())
                    else:
                        delay = base_delay
                    
                    warn(f"调用失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                    debug(f"将在 {delay:.1f} 秒后重试...")
                    
                    if on_retry:
                        on_retry(attempt, e, delay)
                    
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        # 根据函数类型返回不同的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def retry_on_rate_limit(func):
    """专门处理速率限制的重试装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        max_retries = 5
        base_delay = 2.0
        
        for attempt in range(max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e).lower()
                
                # 检查是否是速率限制错误
                if any(keyword in error_msg for keyword in ['rate limit', '429', 'too many requests', 'quota']):
                    if attempt >= max_retries:
                        raise
                    
                    # 速率限制使用更长的延迟
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 5)
                    warn(f"触发速率限制，等待 {delay:.1f} 秒后重试...")
                    await asyncio.sleep(delay)
                else:
                    raise
        
        return None
    
    return wrapper


class RetryableError(Exception):
    """可重试的错误"""
    pass


class NonRetryableError(Exception):
    """不可重试的错误"""
    pass
