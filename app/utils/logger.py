"""
日志配置工具
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime


class LoggerConfig:
    """日志配置类"""
    
    def __init__(self, log_dir: str = "logs", log_level: str = "INFO"):
        self.log_dir = Path(log_dir)
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.ensure_log_directory()
    
    def ensure_log_directory(self):
        """确保日志目录存在"""
        if not self.log_dir.exists():
            self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def setup_logger(
        self, 
        name: str = "app",
        log_file: str = None,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        use_timed_rotation: bool = False
    ) -> logging.Logger:
        """配置日志记录器
        
        Args:
            name: 日志记录器名称
            log_file: 日志文件名（None则使用时间戳）
            max_bytes: 单个日志文件最大大小
            backup_count: 保留的备份文件数量
            use_timed_rotation: 是否使用按时间轮转
            
        Returns:
            配置好的Logger实例
        """
        logger = logging.getLogger(name)
        logger.setLevel(self.log_level)
        
        # 避免重复添加handler
        if logger.handlers:
            return logger
        
        # 创建formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 文件handler
        if log_file is None:
            timestamp = datetime.now().strftime("%Y%m%d")
            log_file = f"app_{timestamp}.log"
        
        log_path = self.log_dir / log_file
        
        if use_timed_rotation:
            # 按时间轮转（每天）
            file_handler = TimedRotatingFileHandler(
                log_path,
                when='midnight',
                interval=1,
                backupCount=backup_count,
                encoding='utf-8'
            )
        else:
            # 按大小轮转
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
        
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    @staticmethod
    def get_logger(name: str = "app") -> logging.Logger:
        """获取logger实例"""
        return logging.getLogger(name)


# 全局日志配置
def setup_logging(log_dir: str = "logs", log_level: str = "INFO") -> logging.Logger:
    """设置全局日志"""
    logger_config = LoggerConfig(log_dir, log_level)
    return logger_config.setup_logger()
