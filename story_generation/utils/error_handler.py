from typing import Any, Dict, Optional, Callable, TypeVar, Union
from functools import wraps
import json
import asyncio
import time
from .logger import StoryLogger

T = TypeVar('T')

class StoryGenerationError(Exception):
    """故事生成基础异常类"""
    def __init__(self, message: str, error_type: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}
        self.timestamp = time.time()

class ContentParsingError(StoryGenerationError):
    """内容解析错误"""
    def __init__(self, message: str, raw_content: str, position: Optional[int] = None):
        super().__init__(
            message=message,
            error_type="CONTENT_PARSING_ERROR",
            details={
                "raw_content": raw_content[:1000],  # 限制长度
                "position": position
            }
        )

class NetworkError(StoryGenerationError):
    """网络相关错误"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(
            message=message,
            error_type="NETWORK_ERROR",
            details={"status_code": status_code}
        )

class TimeoutError(StoryGenerationError):
    """超时错误"""
    def __init__(self, message: str, timeout_seconds: float):
        super().__init__(
            message=message,
            error_type="TIMEOUT_ERROR",
            details={"timeout_seconds": timeout_seconds}
        )

def with_error_handling(logger: StoryLogger):
    """错误处理装饰器"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except json.JSONDecodeError as e:
                error = ContentParsingError(
                    message="JSON解析失败",
                    raw_content=str(e.doc),
                    position=e.pos
                )
                logger.error(
                    f"内容解析失败\n"
                    f"错误信息: {str(e)}\n"
                    f"原始响应:\n{str(e.doc)}\n"
                    f"尝试位置: {e.pos}\n"
                    f"出错行: {str(e.doc).splitlines()[len(str(e.doc)[:e.pos].splitlines())-1]}"
                )
                raise error
            except asyncio.TimeoutError as e:
                error = TimeoutError(
                    message="操作超时",
                    timeout_seconds=kwargs.get('timeout', 0)
                )
                logger.error(f"操作超时: {str(e)}")
                raise error
            except Exception as e:
                logger.error(f"未预期的错误: {str(e)}")
                raise StoryGenerationError(
                    message=f"未预期的错误: {str(e)}",
                    error_type="UNEXPECTED_ERROR"
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except json.JSONDecodeError as e:
                error = ContentParsingError(
                    message="JSON解析失败",
                    raw_content=str(e.doc),
                    position=e.pos
                )
                logger.error(
                    f"内容解析失败\n"
                    f"错误信息: {str(e)}\n"
                    f"原始响应:\n{str(e.doc)}\n"
                    f"尝试位置: {e.pos}\n"
                    f"出错行: {str(e.doc).splitlines()[len(str(e.doc)[:e.pos].splitlines())-1]}"
                )
                raise error
            except Exception as e:
                logger.error(f"未预期的错误: {str(e)}")
                raise StoryGenerationError(
                    message=f"未预期的错误: {str(e)}",
                    error_type="UNEXPECTED_ERROR"
                )
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
