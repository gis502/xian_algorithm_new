"""
Core functionality package
"""
from app.core.env_checker import check_environment
from app.core.venv_manager import check_virtualenv
from app.core.dependency_manager import check_dependencies


def __getattr__(name):
    """延迟导入，只在首次使用时才导入模块"""
    if name == 'AppLauncher':
        from app.core.launcher import AppLauncher
        return AppLauncher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    'check_environment',
    'check_virtualenv',
    'check_dependencies',
    'AppLauncher',
]
