"""
降雨数据Service - 业务逻辑层
"""
import numpy as np
from scipy.spatial import Delaunay, ConvexHull
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

from app.repositories.rainfall_repository import RainfallRepository
from app.utils.logger import setup_logging

logger = setup_logging()


class InterpolationService:
    """插值服务类"""
    
    @staticmethod
    def inverse_distance_weighting(
        points: List[Tuple[float, float]],
        values: List[float],
        grid_lon: np.ndarray,
        grid_lat: np.ndarray,
        power: float = 2.0,
        max_distance: float = 0.5,
        edge_buffer: float = 0.15
    ) -> np.ndarray:
        """
        反距离权重插值 (IDW) - 向量化优化版本
        
        Args:
            points: 已知点坐标 [(lon, lat), ...]
            values: 已知点的值 [rainfall, ...]
            grid_lon: 网格经度数组
            grid_lat: 网格纬度数组
            power: 距离幂次
            max_distance: 最大影响距离（度），超出此距离的点不参与插值
            edge_buffer: 边缘缓冲距离，站点外围扩展此距离再计算凸包
            
        Returns:
            插值后的栅格数据，无效区域为 NaN
        """
        points_array = np.array(points)
        values_array = np.array(values)
        
        # 创建网格
        lon_grid, lat_grid = np.meshgrid(grid_lon, grid_lat)
        result = np.full_like(lon_grid, np.nan)
        
        # 计算站点的凸包（带边缘缓冲）
        hull_mask = None
        if len(points_array) >= 3:
            try:
                # 创建缓冲站点：在原始站点外围添加虚拟点
                buffer_points = InterpolationService._create_buffer_points(
                    points_array, 
                    buffer_distance=edge_buffer
                )
                
                # 合并原始站点和缓冲站点
                all_points = np.vstack([points_array, buffer_points])
                
                # 计算凸包
                hull = ConvexHull(all_points)
                hull_points = all_points[hull.vertices]
                tri = Delaunay(hull_points)
                
                # 向量化判断所有网格点是否在凸包内
                grid_points = np.column_stack([lon_grid.ravel(), lat_grid.ravel()])
                hull_mask = tri.find_simplex(grid_points) >= 0
                hull_mask = hull_mask.reshape(lon_grid.shape)
            except:
                hull_mask = np.ones_like(lon_grid, dtype=bool)
        else:
            hull_mask = np.ones_like(lon_grid, dtype=bool)
        
        # 向量化计算所有网格点到所有站点的距离
        # grid_lon shape: (num_lat, num_lon)
        # points_array[:, 0] shape: (num_stations,)
        # 使用广播机制
        lon_diff = lon_grid[:, :, np.newaxis] - points_array[np.newaxis, np.newaxis, :, 0]
        lat_diff = lat_grid[:, :, np.newaxis] - points_array[np.newaxis, np.newaxis, :, 1]
        distances = np.sqrt(lon_diff**2 + lat_diff**2)
        
        # 过滤超出最大距离的站点
        valid_mask = distances <= max_distance
        
        # 对于每个网格点，检查是否有有效站点
        has_valid_stations = np.any(valid_mask, axis=2)
        
        # 合并凸包掩码和有效站点掩码
        final_mask = hull_mask & has_valid_stations
        
        # 避免除零
        distances = np.where(valid_mask, distances, np.inf)
        distances = np.maximum(distances, 1e-10)
        
        # IDW权重计算
        weights = 1.0 / (distances ** power)
        weights = np.where(valid_mask, weights, 0)
        
        # 加权平均
        weighted_sum = np.sum(weights * values_array[np.newaxis, np.newaxis, :], axis=2)
        weight_total = np.sum(weights, axis=2)
        
        # 计算最终结果
        result = np.where(
            final_mask & (weight_total > 0),
            weighted_sum / weight_total,
            np.nan
        )
        
        return result
    
    @staticmethod
    def get_rainfall_color(rainfall: float) -> str:
        """
        根据降雨量获取颜色（蓝色渐变）
        
        Args:
            rainfall: 降雨量(mm)
            
        Returns:
            颜色字符串 "rgba(r,g,b,a)"
        """
        if rainfall < 0.1:
            return "rgba(200,200,200,0)"  # 透明 - 无雨
        elif rainfall < 10:
            return "rgba(173,216,230,0.5)"     # 浅蓝 - 小雨
        elif rainfall < 25:
            return "rgba(100,149,237,0.6)"     # 矢车菊蓝 - 中雨
        elif rainfall < 50:
            return "rgba(30,144,255,0.7)"      # 道奇蓝 - 大雨
        elif rainfall < 100:
            return "rgba(0,0,205,0.8)"         # 中蓝 - 暴雨
        else:
            return "rgba(0,0,139,0.9)"         # 深蓝 - 大暴雨


class GeoJSONService:
    """GeoJSON生成服务"""
    
    @staticmethod
    def create_feature_collection(
        grid_metadata: Dict[str, Any],
        rainfall_array: np.ndarray,
        grid_lon: np.ndarray,
        grid_lat: np.ndarray
    ) -> Dict[str, Any]:
        """
        创建GeoJSON FeatureCollection用于Cesium渲染
        
        Args:
            grid_metadata: 栅格元数据
            rainfall_array: 降雨量数组
            grid_lon: 经度网格
            grid_lat: 纬度网格
            
        Returns:
            GeoJSON格式的FeatureCollection
        """
        features = []
        
        # 将栅格数据转换为矩形要素
        for i in range(len(grid_lat) - 1):
            for j in range(len(grid_lon) - 1):
                rainfall_value = float(rainfall_array[i, j])
                
                # 跳过无数据的区域
                if np.isnan(rainfall_value) or rainfall_value < 0:
                    continue
                
                # 创建矩形多边形
                lon_min = float(grid_lon[j])
                lon_max = float(grid_lon[j + 1])
                lat_min = float(grid_lat[i])
                lat_max = float(grid_lat[i + 1])
                
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [lon_min, lat_min],
                            [lon_max, lat_min],
                            [lon_max, lat_max],
                            [lon_min, lat_max],
                            [lon_min, lat_min]
                        ]]
                    },
                    "properties": {
                        "rainfall": round(rainfall_value, 2),
                        "color": InterpolationService.get_rainfall_color(rainfall_value)
                    }
                }
                features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "resolution": grid_metadata['resolution'],
                "grid_size": [len(grid_lon), len(grid_lat)],
                "bounds": {
                    "min_lon": float(grid_lon.min()),
                    "max_lon": float(grid_lon.max()),
                    "min_lat": float(grid_lat.min()),
                    "max_lat": float(grid_lat.max())
                }
            }
        }


class RainfallService:
    """降雨数据业务服务类"""
    
    def __init__(self):
        self.repository = RainfallRepository()
        self.interpolation_service = InterpolationService()
        self.geojson_service = GeoJSONService()
    
    def get_stations_data(
        self,
        query_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        获取站点降雨数据
        
        Args:
            query_time: 查询时间（自动查询前12小时数据）
            
        Returns:
            站点数据列表
        """
        return self.repository.query_stations_rainfall(query_time)
    
    def generate_rainfall_grid(
        self,
        query_time: datetime,
        resolution: float = 0.01
    ) -> Dict[str, Any]:
        """
        生成降雨栅格数据
        
        Args:
            query_time: 查询时间（自动查询前12小时数据）
            resolution: 栅格分辨率
            
        Returns:
            GeoJSON格式的栅格数据
        """
        logger.info(f"查询降雨数据: {query_time}")
        
        # 查询站点数据（自动查询前12小时数据）
        stations_data = self.get_stations_data(query_time)
        
        if not stations_data:
            return None
        
        # 提取站点坐标和降雨量（过滤空值）
        valid_stations = [row for row in stations_data if row['rainfall'] is not None]
        
        if not valid_stations:
            logger.warning("所有站点的降雨量数据均为空")
            return None
        
        points = [(row['lon'], row['lat']) for row in valid_stations]
        values = [float(row['rainfall']) for row in valid_stations]
        
        # 确定栅格范围（西安大致范围）
        lon_min, lon_max = 107.5, 109.5
        lat_min, lat_max = 33.5, 34.5
        
        # 创建栅格网格
        num_lon = int((lon_max - lon_min) / resolution) + 1
        num_lat = int((lat_max - lat_min) / resolution) + 1
        
        grid_lon = np.linspace(lon_min, lon_max, num_lon)
        grid_lat = np.linspace(lat_min, lat_max, num_lat)
        
        logger.info(f"生成栅格: {num_lon}x{num_lat}, 分辨率: {resolution}")
        
        # 执行IDW插值（带凸包裁剪和距离阈值）
        rainfall_grid = self.interpolation_service.inverse_distance_weighting(
            points=points,
            values=values,
            grid_lon=grid_lon,
            grid_lat=grid_lat,
            power=2.0,
            max_distance=0.3  # 最大影响距离0.3度（约30公里）
        )
        
        # 创建栅格元数据
        grid_metadata = {
            "query_time": query_time.isoformat(),
            "resolution": resolution,
            "station_count": len(stations_data),
            "grid_size": [num_lon, num_lat]
        }
        
        # 转换为GeoJSON格式
        geojson_data = self.geojson_service.create_feature_collection(
            grid_metadata, rainfall_grid, grid_lon, grid_lat
        )
        
        logger.info("降雨栅格数据生成成功")
        
        return geojson_data
    
    def get_rainfall_at_point(
        self,
        longitude: float,
        latitude: float,
        query_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        查询指定点位的降雨量（使用IDW插值）
        
        Args:
            longitude: 经度
            latitude: 纬度
            query_time: 查询时间（自动查询前12小时数据）
            
        Returns:
            点位降雨量信息
        """
        # 获取站点数据（自动查询前12小时数据）
        stations_data = self.get_stations_data(query_time)
        
        if not stations_data:
            return None
        
        # 提取站点坐标和降雨量
        points = [(row['lon'], row['lat']) for row in stations_data]
        values = [float(row['rainfall']) for row in stations_data]
        
        # 使用IDW插值计算该点的降雨量
        target_point = np.array([[longitude, latitude]])
        points_array = np.array(points)
        
        # 计算距离
        distances = np.sqrt(
            (points_array[:, 0] - longitude) ** 2 + 
            (points_array[:, 1] - latitude) ** 2
        )
        
        # 避免除零
        min_dist = 1e-10
        distances = np.maximum(distances, min_dist)
        
        # IDW公式
        power = 2.0
        weights = 1.0 / (distances ** power)
        rainfall_value = np.sum(weights * values) / np.sum(weights)
        
        # 返回结果
        return {
            "longitude": longitude,
            "latitude": latitude,
            "rainfall": round(float(rainfall_value), 2),
            "level": self._get_rainfall_level(rainfall_value),
            "color": InterpolationService.get_rainfall_color(rainfall_value),
            "station_count": len(stations_data),
            "query_time": query_time.isoformat()
        }
    
    @staticmethod
    def _get_rainfall_level(rainfall: float) -> str:
        """获取降雨等级"""
        if rainfall < 0.1:
            return "无雨"
        elif rainfall < 10:
            return "小雨"
        elif rainfall < 25:
            return "中雨"
        elif rainfall < 50:
            return "大雨"
        elif rainfall < 100:
            return "暴雨"
        else:
            return "大暴雨"
