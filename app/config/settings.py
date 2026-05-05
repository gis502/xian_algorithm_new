"""
配置加载器 - 根据环境自动加载对应配置
"""
import os
from typing import Type
from .base_config import BaseConfig, EnvironmentEnum
from .development import DevelopmentConfig
from .production import ProductionConfig


def get_config_class(environment: str = None) -> Type[BaseConfig]:
    """根据环境获取配置类
    
    Args:
        environment: 环境名称 (development/production)
        
    Returns:
        对应的配置类
    """
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")
    
    config_map = {
        EnvironmentEnum.DEVELOPMENT: DevelopmentConfig,
        EnvironmentEnum.PRODUCTION: ProductionConfig,
    }
    
    try:
        env_enum = EnvironmentEnum(environment)
        return config_map[env_enum]
    except ValueError:
        print(f"警告: 未知环境 '{environment}'，使用默认开发环境配置")
        return DevelopmentConfig


def load_config(environment: str = None) -> BaseConfig:
    """加载配置
    
    Args:
        environment: 环境名称
        
    Returns:
        配置实例
    """
    config_class = get_config_class(environment)
    return config_class()


# 全局配置实例（延迟加载）
_config_instance = None


def get_settings() -> BaseConfig:
    """获取全局配置实例（单例模式）"""
    global _config_instance
    if _config_instance is None:
        environment = os.getenv("ENVIRONMENT", None)
        _config_instance = load_config(environment)
    return _config_instance


def reload_config(environment: str = None):
    """重新加载配置"""
    global _config_instance
    _config_instance = load_config(environment)
