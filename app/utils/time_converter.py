"""
时间转换工具
统一处理标准时间输入与数据库时间格式的转换
"""
from datetime import datetime, timedelta
from typing import Union


class TimeConverter:
    """时间转换器"""
    
    # 数据库时间格式：YYYYMMDDHHmmss（如 20250907070000）
    DB_FORMAT = '%Y%m%d%H%M%S'
    
    # 标准输入格式：2025-07-04 20:00:00 或 2025-07-04T20:00:00
    INPUT_FORMATS = [
        '%Y-%m-%d %H:%M:%S',  # 2025-07-04 20:00:00
        '%Y-%m-%dT%H:%M:%S',  # 2025-07-04T20:00:00
        '%Y-%m-%d %H:%M',     # 2025-07-04 20:00
        '%Y-%m-%dT%H:%M',     # 2025-07-04T20:00
    ]
    
    @staticmethod
    def parse_input_time(time_str: str) -> datetime:
        """
        解析标准时间输入字符串
        
        支持格式：
        - 2025-07-04 20:00:00
        - 2025-07-04T20:00:00
        - 2025-07-04 20:00
        - 2025-07-04T20:00
        
        Args:
            time_str: 时间字符串
            
        Returns:
            datetime对象
            
        Raises:
            ValueError: 时间格式无法识别
        """
        if not time_str:
            raise ValueError("时间字符串不能为空")
        
        # 尝试所有支持的格式
        for fmt in TimeConverter.INPUT_FORMATS:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"无法识别的时间格式: {time_str}，支持格式: {TimeConverter.INPUT_FORMATS}")
    
    @staticmethod
    def to_db_format(dt: datetime) -> int:
        """
        将datetime对象转换为数据库时间格式（YYYYMMDDHHmmss整数）
        
        Args:
            dt: datetime对象
            
        Returns:
            YYYYMMDDHHmmss格式的整数
        """
        return int(dt.strftime(TimeConverter.DB_FORMAT))
    
    @staticmethod
    def from_db_format(db_time: int) -> datetime:
        """
        将数据库时间格式（YYYYMMDDHHmmss整数）转换为datetime对象
        
        Args:
            db_time: YYYYMMDDHHmmss格式的整数
            
        Returns:
            datetime对象
        """
        return datetime.strptime(str(db_time), TimeConverter.DB_FORMAT)
    
    @staticmethod
    def to_db_time_range(query_time: Union[datetime, str], hours: int = 72) -> tuple:
        """
        将查询时间转换为数据库时间范围
        
        Args:
            query_time: 查询时间（datetime对象或标准时间字符串）
            hours: 时间窗口（小时），默认72小时
            
        Returns:
            (start_time, end_time) 元组，均为YYYYMMDDHHmmss格式的整数
        """
        # 如果是字符串，先解析为datetime
        if isinstance(query_time, str):
            query_time = TimeConverter.parse_input_time(query_time)
        
        # 计算时间范围
        end_time = query_time
        start_time = query_time - timedelta(hours=hours)
        
        # 转换为数据库格式
        return (TimeConverter.to_db_format(start_time), TimeConverter.to_db_format(end_time))
    
    @staticmethod
    def get_sql_time_condition(column: str = 'datetime', 
                              query_time: Union[datetime, str] = None,
                              hours: int = 72) -> str:
        """
        生成SQL时间条件片段
        
        Args:
            column: 时间列名，默认'datetime'
            query_time: 查询时间
            hours: 时间窗口（小时）
            
        Returns:
            SQL条件字符串，如 "datetime BETWEEN 20250904070000 AND 20250907070000"
        """
        if query_time is None:
            query_time = datetime.now()
        
        start, end = TimeConverter.to_db_time_range(query_time, hours)
        return f"{column} BETWEEN {start} AND {end}"


# 创建全局实例
time_converter = TimeConverter()