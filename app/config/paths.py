"""
项目配置模块
提供统一的项目路径和配置管理
"""
from pathlib import Path

# 项目根目录（app/config/ 的上两级）
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 日志目录
LOG_DIR = PROJECT_ROOT / "logs"

# 配置文件目录
CONFIG_DIR = PROJECT_ROOT / "app" / "config"

# DBN 配置目录
DBN_CONFIG_DIR = CONFIG_DIR / "dbn"


def get_logger(name: str = "algorithm"):
    """
    获取日志记录器的便捷函数

    Args:
        name: 日志名称

    Returns:
        logging.Logger 实例
    """
    from app.utils.logger import get_logger as _get_logger
    return _get_logger(name, str(LOG_DIR))
