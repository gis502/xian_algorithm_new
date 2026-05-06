"""
降雨数据Repository - 数据访问层
"""
from typing import List, Dict, Any
from datetime import datetime

from app.core.database import db_manager
from app.utils.logger import setup_logging

logger = setup_logging()


class RainfallRepository:
    """降雨数据仓储类"""
    
    @staticmethod
    def query_stations_rainfall(
        query_time: datetime,
        duration: int = 12
    ) -> List[Dict[str, Any]]:
        """
        查询指定时间的站点降雨数据（自动查询前12小时或24小时）
        
        Args:
            query_time: 查询时间
            duration: 持续时间（12或24小时）
            
        Returns:
            站点降雨数据列表
        """
        sql = f"""
        SELECT 
            lon, 
            lat, 
            SUM(rainfall_1h::numeric) AS rainfall
        FROM xian_meteorology
        WHERE datetime BETWEEN (
            to_char(timestamp :query_time - interval '{duration} hours', 'YYYYMMDDHH24MISS')
        )::bigint AND (
            to_char(timestamp :query_time, 'YYYYMMDDHH24MISS')
        )::bigint
        GROUP BY lon, lat
        """
        
        params = {
            "query_time": query_time
        }
        
        try:
            result = db_manager.execute_raw_sql(sql, params)
            logger.info(f"查询到 {len(result)} 个站点数据（{duration}小时）")
            return result
        except Exception as e:
            logger.error(f"查询站点降雨数据失败: {e}")
            raise
