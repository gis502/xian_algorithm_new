"""
降雨数据仓库
负责数据库查询操作
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from app.utils.db_helper import db_helper
from app.utils.time_converter import time_converter


class RainfallRepository:
    """降雨数据仓库"""
    
    def get_max_rainfall_id(self, query_time: Union[datetime, str]) -> Optional[int]:
        """
        查询数据库中指定时间窗口内的最大ID（72小时窗口）

        Args:
            query_time: 查询时间（datetime对象或标准时间字符串，如'2025-07-04 20:00:00'）

        Returns:
            最大ID，如果没有数据则返回None
        """
        # 获取时间范围
        start_time, end_time = time_converter.to_db_time_range(query_time, hours=72)
        
        sql = """
            SELECT max(id) as max_id
            FROM xian_meteorology
            WHERE datetime BETWEEN %s AND %s
        """

        result = db_helper.execute_query_one(sql, (start_time, end_time))

        if result and result.get('max_id'):
            return int(result['max_id'])
        return None
    
    def get_rainfall_stations_data(self, query_time: Union[datetime, str]) -> List[Dict[str, Any]]:
        """
        查询雨量站点降雨数据

        Args:
            query_time: 查询时间（datetime对象或标准时间字符串，如'2025-07-04 20:00:00'）

        Returns:
            站点数据列表，每个元素包含lon, lat, rainfall, duration_hours
        """
        # 获取时间范围
        start_time, end_time = time_converter.to_db_time_range(query_time, hours=72)
        
        # 查询72小时内的降雨时序数据
        sql = """
            SELECT
                lon,
                lat,
                datetime,
                CAST(rainfall_1h AS DOUBLE PRECISION) as rainfall_1h
            FROM xian_meteorology
            WHERE datetime BETWEEN %s AND %s
            ORDER BY lon, lat, datetime DESC
        """

        results = db_helper.execute_query(sql, (start_time, end_time))
        
        if not results:
            return []
        
        # 按站点分组处理
        from itertools import groupby
        
        station_data = []
        for (lon, lat), group in groupby(results, key=lambda r: (r['lon'], r['lat'])):
            accum_rain = 0.0
            duration_hours = 0
            consecutive_no_rain = 0
            
            # 应用"连续3小时无雨截断"规则
            for row in group:
                rainfall = float(row['rainfall_1h']) if row['rainfall_1h'] else 0.0
                if rainfall > 0:
                    accum_rain += rainfall
                    duration_hours += 1
                    consecutive_no_rain = 0
                else:
                    consecutive_no_rain += 1
                    if consecutive_no_rain >= 3:
                        break  # 连续3小时无雨，停止累加
                    if accum_rain > 0:
                        duration_hours += 1
            
            if accum_rain > 0 or duration_hours > 0:
                station_data.append({
                    'lon': float(lon),
                    'lat': float(lat),
                    'rainfall': accum_rain,  # 累计降雨量
                    'duration_hours': duration_hours  # 持续时间
                })
        
        return station_data


# 创建全局实例
rainfall_repository = RainfallRepository()
