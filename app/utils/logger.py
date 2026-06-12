"""
日志工具类
使用 loguru 提供增强的日志功能，支持按天分割、自动清理过期日志
"""
import sys
from pathlib import Path
from loguru import logger


class LoggerManager:
    """日志管理器 - 基于 loguru"""

    _configured = False

    @classmethod
    def get_logger(cls, name: str = "algorithm", log_dir: str = "logs"):
        """
        获取日志记录器（loguru 不需要传统意义上的 logger 实例）
        
        Args:
            name: 日志名称（用于文件命名）
            log_dir: 日志目录
            
        Returns:
            loguru.logger 实例
        """
        if not cls._configured:
            cls._configure_logger(name, log_dir)
        return logger

    @classmethod
    def _configure_logger(cls, name: str, log_dir: str):
        """
        配置 loguru 日志处理器
        
        Args:
            name: 日志名称
            log_dir: 日志目录
        """
        # 移除默认的 stderr handler
        logger.remove()

        # 创建日志目录
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # 控制台 Handler - 彩色输出
        logger.add(
            sink=sys.stderr,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> [<cyan>{thread.name}</cyan>] <level>{level: <5}</level> <blue>{name}</blue> - <level>{message}</level>",
            colorize=True
        )

        # 文件 Handler - 按大小分割，Windows 兼容
        log_file = log_path / f"{name}.log"
        logger.add(
            sink=str(log_file),
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} [{thread.name}] {level: <5} {name} - {message}",
            rotation="50 MB",  # 按大小轮转，避免Windows文件锁定问题
            retention="7 days",  # 保留7天
            compression="zip",  # 压缩旧日志文件
            encoding="utf-8",
            enqueue=True,  # 异步写入，避免文件锁定
            delay=True,  # 延迟打开文件，减少锁定时间
            backtrace=True,  # 完整堆栈跟踪
            diagnose=True  # 详细错误诊断
        )

        cls._configured = True


# 便捷函数
def get_logger(name: str = "algorithm", log_dir: str = "logs"):
    """
    获取日志记录器的便捷函数
    
    Args:
        name: 日志名称
        log_dir: 日志目录
        
    Returns:
        loguru.logger 实例
    """
    return LoggerManager.get_logger(name, log_dir)
