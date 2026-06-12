"""
降雨管理器
负责降雨监测调度和任务编排
"""
import threading
import time
from datetime import datetime
from typing import Optional

from app.utils.logger import get_logger


class RainfallManager:
    """降雨管理器 - 负责监测调度"""
    
    def __init__(self):
        """初始化降雨管理器"""
        self.logger = get_logger()
        self.last_max_id = None  # 记录上次查询的最大ID
        self._query_time: Optional[datetime] = None  # 可动态更新的查询时间（全局变量）
        self._lock = threading.Lock()  # 线程锁，保证时间更新的线程安全
    
    def monitoring_rainfall_station_id(self, query_time: Optional[datetime] = None):
        """
        启动监测线程，定期检查数据库中最大ID是否改变
        
        Args:
            query_time: 查询时间，默认为当前时间
        """
        from app.utils.thread_pool_manager import thread_pool_manager
        
        if query_time is None:
            query_time = datetime.now()
        
        # 存储查询时间到实例变量（线程安全）
        with self._lock:
            self._query_time = query_time
        
        self.logger.info(f"启动降雨站点监测，查询时间: {query_time}")
        
        # 提交监测任务到线程池（不再传时间参数，循环内从 self._query_time 读取）
        thread_pool_manager.submit_task(
            self._monitoring_loop,
            task_name="降雨站点ID监测"
        )
    
    def update_query_time(self, new_time: datetime) -> dict:
        """
        更新查询时间并重置监测状态，触发重新计算
        
        Args:
            new_time: 新的查询时间
        
        Returns:
            包含操作结果的字典
        """
        with self._lock:
            old_time = self._query_time
            self._query_time = new_time
            # 重置 last_max_id 为 None，强制触发重新计算
            self.last_max_id = None
        
        self.logger.info(f"查询时间已更新: {old_time} -> {new_time}，将触发重新计算")
        return {
            "old_time": str(old_time) if old_time else None,
            "new_time": str(new_time),
            "message": "查询时间已更新，将在下一轮监测循环中触发重新计算"
        }
    
    def get_current_query_time(self) -> Optional[datetime]:
        """获取当前查询时间"""
        with self._lock:
            return self._query_time
    
    def _monitoring_loop(self):
        """
        监测循环，定期检查最大ID是否改变
        每次循环从 self._query_time 读取最新的查询时间
        """
        from app.repositories.rainfall_repository import rainfall_repository

        while True:
            try:
                # 每次循环从全局变量读取最新的查询时间
                with self._lock:
                    query_time = self._query_time
                if query_time is None:
                    query_time = datetime.now()
                
                # 查询当前时间窗口内的最大ID
                max_id = rainfall_repository.get_max_rainfall_id(query_time)
                
                # 如果ID为空（刚启动）或者改变，则生成降雨栅格
                if self.last_max_id is None or max_id != self.last_max_id:
                    from app.utils.thread_pool_manager import thread_pool_manager
                    
                    self.logger.info(f"检测到数据更新，旧ID: {self.last_max_id}, 新ID: {max_id}, 查询时间: {query_time}")
                    
                    # 提交栅格生成任务
                    thread_pool_manager.submit_task(
                        self._generate_rainfall_grid_task,
                        query_time,
                        max_id,
                        task_name=f"降雨栅格生成_{max_id}"
                    )
                    
                    # 更新最后记录的ID
                    self.last_max_id = max_id
                
                # 等待一段时间后再次检查
                time.sleep(5)

            except Exception as e:
                self.logger.error(f"监测循环出错: {e}", exc_info=True)
                time.sleep(60)  # 出错后等待1分钟再继续
    
    def _generate_rainfall_grid_task(self, query_time: datetime, max_id: int):
        """
        生成降雨栅格的任务函数

        Args:
            query_time: 查询时间
            max_id: 最大ID
        """
        try:
            from app.repositories.rainfall_repository import rainfall_repository
            from app.services.rainfall_grid_service import rainfall_grid_service

            self.logger.info(f"开始生成降雨栅格，查询时间: {query_time}, ID: {max_id}")

            # 1. 查询雨量站点数据
            station_data = rainfall_repository.get_rainfall_stations_data(query_time)
            
            if not station_data:
                self.logger.warning(f"未查询到降雨站点数据，时间: {query_time}")
                return
            
            self.logger.info(f"查询到 {len(station_data)} 个站点数据")
            
            # 2. 执行插值算法（已包含边缘优化）
            grid_data = rainfall_grid_service.interpolate_rainfall(station_data)
            
            # 3. 生成PNG图片
            png_path = rainfall_grid_service.save_rainfall_grid_png(grid_data, max_id)
            
            if png_path:
                # 5. 存储信息到Redis
                rainfall_grid_service.store_to_redis(png_path, max_id, query_time, station_data)
                
                self.logger.info(f"降雨栅格生成完成，路径: {png_path}")
            else:
                self.logger.error("降雨栅格生成失败")
                
        except Exception as e:
            self.logger.error(f"生成降雨栅格任务出错: {e}", exc_info=True)


# 创建全局实例
rainfall_manager = RainfallManager()