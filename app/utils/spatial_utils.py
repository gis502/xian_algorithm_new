"""
空间计算工具模块
提供纯数学计算功能（不涉及数据库查询）
"""
import math
from typing import Tuple


class SpatialUtils:
    """空间计算工具类 - 纯数学计算"""

    EARTH_RADIUS = 6371000  # 地球半径（米）

    @staticmethod
    def haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """
        使用Haversine公式计算两点间的球面距离

        Args:
            lon1: 点1经度
            lat1: 点1纬度
            lon2: 点2经度
            lat2: 点2纬度

        Returns:
            距离（米）
        """
        lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        distance = SpatialUtils.EARTH_RADIUS * c

        return distance

    @staticmethod
    def calculate_buffer_area(radius: float) -> float:
        """
        计算缓冲区面积

        Args:
            radius: 半径（米）

        Returns:
            面积（平方米）
        """
        return math.pi * radius ** 2

    @staticmethod
    def calculate_density(total_length: float, area: float) -> float:
        """
        计算密度（长度/面积）

        Args:
            total_length: 总长度（米）
            area: 面积（平方米）

        Returns:
            密度（m/m²）
        """
        if area <= 0:
            return 0.0
        return total_length / area


# 创建全局实例
spatial_utils = SpatialUtils()
