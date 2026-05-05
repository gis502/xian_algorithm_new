"""
开发环境配置
"""
from .database_config import DatabaseConfig
from .base_config import EnvironmentEnum


class DevelopmentConfig(DatabaseConfig):
    """开发环境配置 - 只覆盖与生产不同的配置"""
    
    ENVIRONMENT: EnvironmentEnum = EnvironmentEnum.DEVELOPMENT
    
    # 调试和日志
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    
    # 开发特性
    RELOAD: bool = True
    
    class Config:
        env_file = ".env.development"
        case_sensitive = True
