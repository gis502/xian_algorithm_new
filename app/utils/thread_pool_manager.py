"""
线程池管理工具类
提供线程池的创建、管理和任务提交功能
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Any, Optional
from app.utils.logger import get_logger


class ThreadPoolManager:
    """线程池管理器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """单例模式确保只有一个线程池管理器实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, max_workers: int = 10, thread_name_prefix: str = "Worker"):
        """
        初始化线程池管理器
        
        Args:
            max_workers: 线程池最大工作线程数
            thread_name_prefix: 线程名称前缀
        """
        # 防止重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.max_workers = max_workers
        self.thread_name_prefix = thread_name_prefix
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix=thread_name_prefix
        )
        self.futures = {}  # 存储提交的任务future对象
        self.tasks_count = 0  # 任务计数器
        self.completed_tasks = 0  # 已完成任务计数
        self._shutdown = False
        self.logger = get_logger()
        self._initialized = True
        
        self.logger.info(f"线程池管理器已初始化，最大工作线程数: {max_workers}")
    
    @classmethod
    def get_instance(cls, max_workers: int = 10, thread_name_prefix: str = "Worker") -> 'ThreadPoolManager':
        """
        获取线程池管理器单例实例
        
        Args:
            max_workers: 线程池最大工作线程数
            thread_name_prefix: 线程名称前缀
            
        Returns:
            ThreadPoolManager: 线程池管理器实例
        """
        if cls._instance is None:
            cls._instance = cls(max_workers, thread_name_prefix)
        return cls._instance
    
    def submit_task(self, func: Callable, *args, task_name: Optional[str] = None, **kwargs) -> Future:
        """
        提交任务到线程池
        
        Args:
            func: 要执行的函数
            *args: 函数的位置参数
            task_name: 任务名称（可选）
            **kwargs: 函数的关键字参数
            
        Returns:
            Future: 代表异步执行结果的Future对象
        """
        if self._shutdown:
            raise RuntimeError("线程池已关闭，无法提交新任务")
        
        self.tasks_count += 1
        if not task_name:
            task_name = f"Task_{self.tasks_count}"
        
        future = self.executor.submit(func, *args, **kwargs)
        self.futures[task_name] = future
        
        # 添加回调函数，在任务完成时更新计数
        future.add_done_callback(lambda f: self._on_task_complete(task_name))
        
        self.logger.debug(f"任务 '{task_name}' 已提交到线程池")
        return future
    
    def _on_task_complete(self, task_name: str):
        """
        任务完成时的回调处理
        
        Args:
            task_name: 完成的任务名称
        """
        self.completed_tasks += 1
        if task_name in self.futures:
            del self.futures[task_name]
        self.logger.debug(f"任务 '{task_name}' 已完成，当前完成任务数: {self.completed_tasks}")
    
    def submit_and_wait(self, func: Callable, *args, timeout: Optional[float] = None, **kwargs) -> Any:
        """
        提交任务并等待结果
        
        Args:
            func: 要执行的函数
            *args: 函数的位置参数
            timeout: 超时时间（秒），None表示无限等待
            **kwargs: 函数的关键字参数
            
        Returns:
            Any: 任务执行结果
        """
        future = self.submit_task(func, *args, **kwargs)
        try:
            result = future.result(timeout=timeout)
            return result
        except Exception as e:
            self.logger.error(f"任务执行出错: {e}")
            raise
    
    def shutdown(self, wait: bool = True):
        """
        关闭线程池
        
        Args:
            wait: 是否等待所有任务完成后再关闭
        """
        if not self._shutdown:
            self._shutdown = True
            self.logger.info("正在关闭线程池...")
            
            # 等待所有任务完成
            if wait:
                self.executor.shutdown(wait=True)
                self.logger.info("线程池已关闭，所有任务已完成")
            else:
                self.executor.shutdown(wait=False)
                self.logger.info("线程池已关闭，未完成任务将被取消")
                
            # 清理future引用
            self.futures.clear()
    
    def get_active_threads_count(self) -> int:
        """
        获取活跃线程数量
        
        Returns:
            int: 活跃线程数
        """
        # 通过统计未完成的future数量来估算活跃线程数
        active_futures = [f for f in self.futures.values() if not f.done()]
        return len(active_futures)
    
    def get_pool_status(self) -> dict:
        """
        获取线程池状态信息
        
        Returns:
            dict: 包含线程池状态信息的字典
        """
        return {
            "max_workers": self.max_workers,
            "active_threads": self.get_active_threads_count(),
            "total_tasks_submitted": self.tasks_count,
            "completed_tasks": self.completed_tasks,
            "pending_tasks": len([f for f in self.futures.values() if not f.done()]),
            "is_shutdown": self._shutdown
        }
    
    def wait_for_completion(self, timeout: Optional[float] = None):
        """
        等待所有任务完成
        
        Args:
            timeout: 超时时间（秒），None表示无限等待
        """
        start_time = time.time()
        while True:
            pending_futures = [f for f in self.futures.values() if not f.done()]
            if not pending_futures:
                break
                
            if timeout and (time.time() - start_time) > timeout:
                self.logger.warning(f"等待任务完成超时 ({timeout}s)")
                break
                
            time.sleep(0.1)  # 短暂休眠以减少CPU占用


def block_main_thread():
    """
    阻塞主线程，防止程序立即退出
    通常用于保持服务持续运行
    """
    logger = get_logger()
    logger.info("主线程进入阻塞状态，按 Ctrl+C 退出...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到中断信号，准备退出...")
        # 获取线程池管理器实例并关闭
        pool_manager = ThreadPoolManager.get_instance()
        pool_manager.shutdown(wait=True)
        logger.info("程序正常退出")


# 全局线程池管理器实例
thread_pool_manager = ThreadPoolManager.get_instance()