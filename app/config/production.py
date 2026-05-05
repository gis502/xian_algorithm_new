"""
生产环境配置
"""
from .database_config import DatabaseConfig
from .base_config import EnvironmentEnum


class ProductionConfig(DatabaseConfig):
    """生产环境配置 - 只覆盖性能和安全相关配置"""
    
    ENVIRONMENT: EnvironmentEnum = EnvironmentEnum.PRODUCTION
    
    # 调试和日志
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    
    # 生产特性
    RELOAD: bool = False
    
    # 数据库连接池（生产环境需要更大）
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    
    class Config:
        env_file = ".env.production"
        case_sensitive = True
