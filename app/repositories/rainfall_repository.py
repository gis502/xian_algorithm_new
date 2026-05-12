"""
降雨数据仓库
负责数据库查询操作
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.utils.db_helper import db_helper


class RainfallRepository:
    """降雨数据仓库"""
    
    def get_max_rainfall_id(self, query_time: datetime) -> Optional[int]:
        """
        查询数据库中指定时间窗口内的最大ID
        
        Args:
            query_time: 查询时间
            
        Returns:
            最大ID，如果没有数据则返回None
        """
        sql = """
            SELECT max(id) as max_id 
            FROM xian_meteorology 
            WHERE datetime BETWEEN (
                to_char(timestamp %s - interval '12 hours', 'YYYYMMDDHH24MISS')
            )::bigint AND (
                to_char(timestamp %s, 'YYYYMMDDHH24MISS')
            )::bigint
        """
        
        result = db_helper.execute_query_one(sql, (query_time, query_time))
        
        if result and result.get('max_id'):
            return int(result['max_id'])
        return None
    
    def get_rainfall_stations_data(self, query_time: datetime) -> List[Dict[str, Any]]:
        """
        查询雨量站点降雨数据
        
        Args:
            query_time: 查询时间
            
        Returns:
            站点数据列表，每个元素包含lon, lat, rainfall
        """
        sql = """
            SELECT 
                lon, 
                lat, 
                SUM(rainfall_1h::numeric) AS rainfall
            FROM xian_meteorology
            WHERE datetime BETWEEN (
                to_char(timestamp %s - interval '12 hours', 'YYYYMMDDHH24MISS')
            )::bigint AND (
                to_char(timestamp %s, 'YYYYMMDDHH24MISS')
            )::bigint
            GROUP BY lon, lat
        """
        
        results = db_helper.execute_query(sql, (query_time, query_time))
        
        # 转换数据格式
        station_data = []
        for row in results:
            if row.get('lon') and row.get('lat'):
                station_data.append({
                    'lon': float(row['lon']),
                    'lat': float(row['lat']),
                    'rainfall': float(row['rainfall']) if row.get('rainfall') else 0.0
                })
        
        return station_data


# 创建全局实例
rainfall_repository = RainfallRepository()
