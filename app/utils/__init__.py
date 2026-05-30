"""
Utility functions package
"""


def __getattr__(name):
    """延迟导入，只在首次使用时才导入模块"""
    if name in ('db_helper', 'PostgresSQLHelper'):
        from app.utils.db_helper import db_helper, PostgresSQLHelper
        return db_helper if name == 'db_helper' else PostgresSQLHelper
    elif name in ('thread_pool_manager', 'ThreadPoolManager', 'block_main_thread'):
        from app.utils.thread_pool_manager import (
            thread_pool_manager,
            ThreadPoolManager,
            block_main_thread
        )
        if name == 'thread_pool_manager':
            return thread_pool_manager
        elif name == 'ThreadPoolManager':
            return ThreadPoolManager
        else:
            return block_main_thread
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ['db_helper', 'PostgresSQLHelper', 'thread_pool_manager', 'ThreadPoolManager', 'block_main_thread']
