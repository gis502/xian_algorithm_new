"""
日志工具类
支持按天分割、自动清理过期日志
"""
import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timedelta


class LoggerManager:
    """日志管理器"""

    _loggers = {}

    @classmethod
    def get_logger(cls, name: str = "algorithm", log_dir: str = "logs") -> logging.Logger:
        """
        获取日志记录器
        
        Args:
            name: 日志名称
            log_dir: 日志目录
            
        Returns:
            logging.Logger 实例
        """
        if name in cls._loggers:
            return cls._loggers[name]

        # 创建日志目录
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # 创建 logger
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # 避免重复添加 handler
        if logger.handlers:
            cls._loggers[name] = logger
            return logger

        # 日志格式
        formatter = logging.Formatter(
            '%(asctime)s [%(threadName)s] %(levelname)-5s %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 控制台 Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 文件 Handler - 按天分割
        log_file = log_path / f"{name}.log"
        file_handler = TimedRotatingFileHandler(
            filename=str(log_file),
            when='midnight',
            interval=1,
            backupCount=7,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # 设置日志文件命名格式
        file_handler.suffix = "%Y-%m-%d.log"

        logger.addHandler(file_handler)

        cls._loggers[name] = logger
        return logger


# 便捷函数
def get_logger(name: str = "algorithm", log_dir: str = "logs") -> logging.Logger:
    """
    获取日志记录器的便捷函数
    
    Args:
        name: 日志名称
        log_dir: 日志目录
        
    Returns:
        logging.Logger 实例
    """
    return LoggerManager.get_logger(name, log_dir)
