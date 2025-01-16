"""故事生成日志管理器"""

import logging
import os
import time
import json
from datetime import datetime
from typing import Optional, Dict, Any, Union
from functools import wraps
import threading
import asyncio
from ..config.settings import Settings

class StoryLogger:
    """故事生成日志管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StoryLogger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # 获取配置
        settings = Settings()
        log_config = settings.logging
        
        # 创建日志目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = os.path.join("logs", timestamp)
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 配置日志格式
        self.logger = logging.getLogger("StoryGeneration")
        self.logger.setLevel(log_config["level"])
        
        # 文件处理器 - 详细日志
        detailed_handler = logging.FileHandler(
            os.path.join(self.log_dir, "detailed.log"), 
            encoding='utf-8'
        )
        detailed_handler.setLevel(logging.DEBUG)
        
        # 文件处理器 - 错误日志
        error_handler = logging.FileHandler(
            os.path.join(self.log_dir, "error.log"), 
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_config["level"])
        
        # 日志格式
        detailed_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(context)s\n"
            "%(message)s\n"
        )
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(context)s - %(message).200s"
        )
        
        detailed_handler.setFormatter(detailed_formatter)
        error_handler.setFormatter(detailed_formatter)
        console_handler.setFormatter(console_formatter)
        
        # 添加处理器
        self.logger.addHandler(detailed_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)
        
        # 初始化性能指标
        self.performance_metrics = {}
        
        self._initialized = True
    
    def _format_context(self, role: Optional[str] = None, **kwargs) -> str:
        """格式化上下文信息"""
        context = {
            "role": role or "unknown",
            "process_id": os.getpid(),
            "thread_id": threading.get_ident(),
            "task_id": id(asyncio.current_task()) if asyncio.current_task() else None,
            **kwargs
        }
        return json.dumps(context, ensure_ascii=False)
    
    def _log(self, level: str, message: str, role: Optional[str] = None, **kwargs):
        """通用日志记录方法"""
        context = self._format_context(role, **kwargs)
        extra = {'context': context}
        
        if role:
            message = f"[{role}] {message}"
            
        getattr(self.logger, level)(message, extra=extra)
    
    def debug(self, message: str, role: Optional[str] = None, **kwargs):
        """记录调试信息"""
        self._log('debug', message, role, **kwargs)
    
    def info(self, message: str, role: Optional[str] = None, **kwargs):
        """记录一般信息"""
        self._log('info', message, role, **kwargs)
    
    def warning(self, message: str, role: Optional[str] = None, **kwargs):
        """记录警告信息"""
        self._log('warning', message, role, **kwargs)
    
    def error(self, message: str, role: Optional[str] = None, **kwargs):
        """记录错误信息"""
        self._log('error', message, role, **kwargs)
    
    def critical(self, message: str, role: Optional[str] = None, **kwargs):
        """记录严重错误信息"""
        self._log('critical', message, role, **kwargs)
    
    def start_operation(self, operation_name: str, **context) -> str:
        """
        开始记录操作性能
        
        Args:
            operation_name: 操作名称
            **context: 上下文信息
            
        Returns:
            str: 操作ID
        """
        operation_id = f"{operation_name}_{time.time_ns()}"
        self.performance_metrics[operation_id] = {
            "name": operation_name,
            "start_time": time.time(),
            "context": context
        }
        return operation_id
    
    def end_operation(self, operation_id: str, success: bool = True, **metrics):
        """
        结束操作性能记录
        
        Args:
            operation_id: 操作ID
            success: 是否成功
            **metrics: 性能指标
        """
        if operation_id not in self.performance_metrics:
            return
            
        operation = self.performance_metrics[operation_id]
        duration = time.time() - operation["start_time"]
        
        # 记录性能指标
        self.info(
            f"操作完成: {operation['name']}\n"
            f"耗时: {duration:.2f}秒\n"
            f"状态: {'成功' if success else '失败'}\n"
            f"指标: {json.dumps(metrics, ensure_ascii=False, indent=2)}",
            role=operation["context"].get("role", "Performance"),
            operation_id=operation_id,
            duration=duration,
            success=success,
            **metrics
        )
        
        del self.performance_metrics[operation_id]

def log_operation(logger: StoryLogger):
    """操作日志装饰器"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            operation_name = f"{func.__module__}.{func.__name__}"
            operation_id = logger.start_operation(operation_name)
            try:
                result = await func(*args, **kwargs)
                logger.end_operation(operation_id, success=True)
                return result
            except Exception as e:
                logger.end_operation(operation_id, success=False, error=str(e))
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            operation_name = f"{func.__module__}.{func.__name__}"
            operation_id = logger.start_operation(operation_name)
            try:
                result = func(*args, **kwargs)
                logger.end_operation(operation_id, success=True)
                return result
            except Exception as e:
                logger.end_operation(operation_id, success=False, error=str(e))
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
