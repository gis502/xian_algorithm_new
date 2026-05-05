"""
基础配置类
"""
from pydantic_settings import BaseSettings
from enum import Enum


class EnvironmentEnum(str, Enum):
    """环境枚举"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class BaseConfig(BaseSettings):
    """基础配置类"""
    
    # 应用基本信息
    APP_NAME: str = "西安项目算法"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: EnvironmentEnum = EnvironmentEnum.DEVELOPMENT
    
    # 调试模式
    DEBUG: bool = True
    
    # API配置
    API_HOST: str = "127.0.0.1"  # 默认只监听本地
    API_PORT: int = 8000
    
    # CORS配置（默认只允许localhost）
    CORS_ORIGINS: list = ["http://localhost", "http://127.0.0.1"]
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    
    class Config:
        env_file = ".env.development"  # 默认使用开发环境配置
        case_sensitive = True
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.ENVIRONMENT == EnvironmentEnum.DEVELOPMENT
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.ENVIRONMENT == EnvironmentEnum.PRODUCTION
