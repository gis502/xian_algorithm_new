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
    def _create_buffer_points(
        points_array: np.ndarray
    ) -> np.ndarray:
        """
        创建缓冲点：在原始站点外围生成虚拟点以扩展插值区域
        
        Args:
            points_array: 原始站点坐标数组
            
        Returns:
            缓冲点坐标数组
        """
        # 计算站点分布的中心
        center = np.mean(points_array, axis=0)
        
        # 计算站点到中心的最大距离
        distances_from_center = np.sqrt(np.sum((points_array - center) ** 2, axis=1))
        np.max(distances_from_center)
        
        # 在站点外围生成缓冲点（沿着各个方向扩展）
        buffer_points = []
        num_angles = 360  # 每隔1度生成一个缓冲点
        
        for angle_deg in range(0, 360, 360 // num_angles):
            angle_rad = np.radians(angle_deg)
            # 在凸包边界外扩展
            for scale in [1.05, 1.1, 1.15]:
                # 找到该方向上最远的站点
                direction = np.array([np.cos(angle_rad), np.sin(angle_rad)])
                projections = points_array @ direction
                max_idx = np.argmax(projections)
                
                # 在该方向上扩展
                base_point = points_array[max_idx]
                buffer_point = center + (base_point - center) * scale
                buffer_points.append(buffer_point)
        
        return np.array(buffer_points)
    
    @staticmethod
    def gaussian_smoothing(
        grid_data: np.ndarray,
        sigma: float = 1.5
    ) -> np.ndarray:
        """
        高斯平滑滤波，减少边缘突变
        
        Args:
            grid_data: 栅格数据
            sigma: 高斯核标准差
            
        Returns:
            平滑后的栅格数据
        """
        from scipy.ndimage import gaussian_filter
        
        # 只对有效数据进行平滑
        valid_mask = ~np.isnan(grid_data)
        if not np.any(valid_mask):
            return grid_data
        
        # 填充NaN值以便平滑
        filled_data = grid_data.copy()
        mean_val = np.nanmean(grid_data)
        filled_data[~valid_mask] = mean_val
        
        # 应用高斯滤波
        smoothed = gaussian_filter(filled_data, sigma=sigma)
        
        # 恢复原始NaN区域
        result = np.where(valid_mask, smoothed, np.nan)
        
        return result
    
    @staticmethod
    def calculate_adaptive_max_distance(
        points_array: np.ndarray,
        base_distance: float = 0.3,
        min_distance: float = 0.15,
        max_distance: float = 0.5
    ) -> float:
        """
        根据站点密度自适应计算最大影响距离
        
        Args:
            points_array: 站点坐标数组
            base_distance: 基础距离
            min_distance: 最小距离
            max_distance: 最大距离
            
        Returns:
            自适应的最大影响距离
        """
        if len(points_array) < 3:
            return base_distance
        
        # 计算站点间的平均距离
        from scipy.spatial import distance_matrix
        dist_matrix = distance_matrix(points_array, points_array)
        
        # 排除对角线（自身距离为0）
        np.fill_diagonal(dist_matrix, np.inf)
        avg_distance = np.mean(np.min(dist_matrix, axis=1))
        
        # 根据平均距离调整max_distance
        adaptive_distance = avg_distance * 3  # 约3倍平均站点间距
        
        # 限制在合理范围内
        return np.clip(adaptive_distance, min_distance, max_distance)
    
    @staticmethod
    def inverse_distance_weighting(
        points: List[Tuple[float, float]],
        values: List[float],
        grid_lon: np.ndarray,
        grid_lat: np.ndarray,
        power: float = 2.0,
        max_distance: float = None,
        use_adaptive_distance: bool = True,
        apply_smoothing: bool = True,
        smoothing_sigma: float = 1.0
    ) -> np.ndarray:
        """
        反距离权重插值 (IDW) - 优化版本
        改进：
        1. 高斯核衰减替代简单幂律
        2. 自适应距离阈值
        3. 边缘渐变处理
        4. 高斯平滑减少突变
        
        Args:
            points: 已知点坐标 [(lon, lat), ...]
            values: 已知点的值 [rainfall, ...]
            grid_lon: 网格经度数组
            grid_lat: 网格纬度数组
            power: 距离幂次（基础值）
            max_distance: 最大影响距离（度），None则自适应计算
            use_adaptive_distance: 是否使用自适应距离
            apply_smoothing: 是否应用平滑
            smoothing_sigma: 平滑强度
            
        Returns:
            插值后的栅格数据，无效区域为 NaN
        """
        points_array = np.array(points)
        values_array = np.array(values)
        
        # 创建网格
        lon_grid, lat_grid = np.meshgrid(grid_lon, grid_lat)
        result = np.full_like(lon_grid, np.nan)
        
        # 自适应计算最大距离
        if use_adaptive_distance or max_distance is None:
            actual_max_distance = InterpolationService.calculate_adaptive_max_distance(
                points_array
            )
            if max_distance is not None:
                actual_max_distance = min(actual_max_distance, max_distance)
        else:
            actual_max_distance = max_distance
        
        logger.info(f"使用最大影响距离: {actual_max_distance:.3f} 度")
        
        # 计算站点的凸包（带边缘缓冲）
        hull_mask = None
        confidence_mask = None  # 置信度掩码
        if len(points_array) >= 3:
            try:
                # 创建缓冲站点：在原始站点外围添加虚拟点
                buffer_points = InterpolationService._create_buffer_points(
                    points_array
                )
                
                # 合并原始站点和缓冲站点
                all_points = np.vstack([points_array, buffer_points])
                
                # 计算凸包
                hull = ConvexHull(all_points)
                hull_points = all_points[hull.vertices]
                tri = Delaunay(hull_points)
                
                # 向量化判断所有网格点是否在凸包内
                grid_points = np.column_stack([lon_grid.ravel(), lat_grid.ravel()])
                hull_indices = tri.find_simplex(grid_points)
                hull_mask = hull_indices >= 0
                hull_mask = hull_mask.reshape(lon_grid.shape)
                
                # 计算置信度：基于到最近站点的距离
                # 在凸包内但远离站点的区域降低置信度
                from scipy.spatial import distance_matrix
                grid_valid = grid_points[hull_mask.ravel()]
                if len(grid_valid) > 0:
                    dist_to_stations = distance_matrix(grid_valid, points_array)
                    min_distances = np.min(dist_to_stations, axis=1)
                    
                    # 创建置信度掩码（距离越远，置信度越低）
                    confidence = np.ones(len(grid_points))
                    confidence[hull_mask.ravel()] = np.exp(-min_distances / actual_max_distance)
                    confidence_mask = confidence.reshape(lon_grid.shape)
                else:
                    confidence_mask = np.ones_like(lon_grid)
                    
            except Exception as e:
                logger.warning(f"凸包计算失败: {e}，使用全区域插值")
                hull_mask = np.ones_like(lon_grid, dtype=bool)
                confidence_mask = np.ones_like(lon_grid)
        else:
            hull_mask = np.ones_like(lon_grid, dtype=bool)
            confidence_mask = np.ones_like(lon_grid)
        
        # 向量化计算所有网格点到所有站点的距离
        lon_diff = lon_grid[:, :, np.newaxis] - points_array[np.newaxis, np.newaxis, :, 0]
        lat_diff = lat_grid[:, :, np.newaxis] - points_array[np.newaxis, np.newaxis, :, 1]
        distances = np.sqrt(lon_diff**2 + lat_diff**2)
        
        # 过滤超出最大距离的站点
        valid_mask = distances <= actual_max_distance
        
        # 对于每个网格点，检查是否有有效站点
        has_valid_stations = np.any(valid_mask, axis=2)
        
        # 合并凸包掩码和有效站点掩码
        final_mask = hull_mask & has_valid_stations
        
        # 避免除零
        distances = np.where(valid_mask, distances, np.inf)
        distances = np.maximum(distances, 1e-10)
        
        # 优化的权重计算：结合幂律和高斯衰减
        # 近处使用幂律，远处使用高斯衰减使过渡更平滑
        power_weights = 1.0 / (distances ** power)
        gaussian_weights = np.exp(-0.5 * (distances / (actual_max_distance * 0.5)) ** 2)
        
        # 混合权重：距离越远，高斯权重占比越大
        distance_ratio = distances / actual_max_distance
        mix_factor = np.clip(distance_ratio, 0, 1)
        weights = (1 - mix_factor) * power_weights + mix_factor * gaussian_weights
        
        weights = np.where(valid_mask, weights, 0)
        
        # 加权平均
        weighted_sum = np.sum(weights * values_array[np.newaxis, np.newaxis, :], axis=2)
        weight_total = np.sum(weights, axis=2)
        
        # 计算基础插值结果（使用 errstate 忽略预期的除零警告，np.where 已安全过滤）
        with np.errstate(divide='ignore', invalid='ignore'):
            result = np.where(
                final_mask & (weight_total > 0),
                weighted_sum / weight_total,
                np.nan
            )
        
        # 应用置信度调整：边缘区域向邻近值渐变
        if confidence_mask is not None:
            # 计算全局平均降雨量作为边缘区域的基准
            valid_rainfall = result[final_mask]
            if len(valid_rainfall) > 0:
                mean_rainfall = np.mean(valid_rainfall)
                # 边缘区域向平均值渐变
                result = np.where(
                    final_mask,
                    result,
                    np.nan
                )
                # 根据置信度调整结果，低置信度区域向均值靠拢
                adjusted_result = result * confidence_mask + mean_rainfall * (1 - confidence_mask)
                result = np.where(final_mask, adjusted_result, np.nan)
        
        # 应用高斯平滑减少边缘突变
        if apply_smoothing:
            result = InterpolationService.gaussian_smoothing(result, sigma=smoothing_sigma)
        
        return result
    
    @staticmethod
    def get_rainfall_color(rainfall: float, duration: int = 12) -> str:
        """
        根据降雨量获取颜色（按照国标）
        
        Args:
            rainfall: 降雨量(mm)
            duration: 持续时间（12或24小时）
            
        Returns:
            颜色字符串 "rgba(r,g,b,a)"
        """
        # 国标降雨等级颜色映射
        if rainfall < 0.1:
            return "rgba(200,200,200,0)"  # 透明 - 微量降雨（零星小雨）
        elif rainfall < 10 if duration == 12 else 9.9:
            return "rgba(0,0,255,0.4)"      # 浅蓝 - 小雨
        elif rainfall < 15 if duration == 12 else 25:
            return "rgba(0,255,255,0.5)"    # 青色 - 中雨
        elif rainfall < 30 if duration == 12 else 50:
            return "rgba(0,255,0,0.6)"      # 绿色 - 大雨
        elif rainfall < 70 if duration == 12 else 100:
            return "rgba(255,255,0,0.7)"    # 黄色 - 暴雨
        elif rainfall < 140 if duration == 12 else 250:
            return "rgba(255,165,0,0.8)"    # 橙色 - 大暴雨
        else:
            return "rgba(255,0,0,0.9)"      # 红色 - 特大暴雨


class GeoJSONService:
    """GeoJSON生成服务"""
    
    @staticmethod
    def create_feature_collection(
        grid_metadata: Dict[str, Any],
        rainfall_array: np.ndarray,
        grid_lon: np.ndarray,
        grid_lat: np.ndarray,
        duration: int = 12
    ) -> Dict[str, Any]:
        """
        创建GeoJSON FeatureCollection用于Cesium渲染
        
        Args:
            grid_metadata: 栅格元数据
            rainfall_array: 降雨量数组
            grid_lon: 经度网格
            grid_lat: 纬度网格
            duration: 持续时间（12或24小时）
            
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
                        "level": RainfallService._get_rainfall_level(rainfall_value, duration),
                        "color": InterpolationService.get_rainfall_color(rainfall_value, duration)
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
        query_time: datetime,
        duration: int = 12
    ) -> List[Dict[str, Any]]:
        """
        获取站点降雨数据
        
        Args:
            query_time: 查询时间（自动查询前12小时或24小时数据）
            duration: 持续时间（12或24小时）
            
        Returns:
            站点数据列表
        """
        return self.repository.query_stations_rainfall(query_time, duration)
    
    def generate_rainfall_grid(
        self,
        query_time: datetime,
        resolution: float = 0.01,
        duration: int = 12
    ) -> Dict[str, Any]:
        """
        生成降雨栅格数据
        
        Args:
            query_time: 查询时间（自动查询前12小时或24小时数据）
            resolution: 栅格分辨率
            duration: 持续时间（12或24小时）
            
        Returns:
            GeoJSON格式的栅格数据
        """
        logger.info(f"查询降雨数据: {query_time}, 持续时间: {duration}小时")
        
        # 查询站点数据（自动查询前12小时或24小时数据）
        stations_data = self.get_stations_data(query_time, duration)
        
        if not stations_data:
            return None
        
        # 提取站点坐标和降雨量（过滤空值）
        valid_stations = [row for row in stations_data if row['rainfall'] is not None]
        
        if not valid_stations:
            logger.warning("所有站点的降雨量数据均为空")
            return None
        
        points = [(row['lon'], row['lat']) for row in valid_stations]
        values = [float(row['rainfall']) for row in valid_stations]
        
        # 确定栅格范围
        lon_min, lon_max = 107, 110
        lat_min, lat_max = 33, 35
        
        # 创建栅格网格
        num_lon = int((lon_max - lon_min) / resolution) + 1
        num_lat = int((lat_max - lat_min) / resolution) + 1
        
        grid_lon = np.linspace(lon_min, lon_max, num_lon)
        grid_lat = np.linspace(lat_min, lat_max, num_lat)
        
        logger.info(f"生成栅格: {num_lon}x{num_lat}, 分辨率: {resolution}")
        
        # 执行IDW插值（优化版本：自适应距离、混合权重、平滑处理）
        rainfall_grid = self.interpolation_service.inverse_distance_weighting(
            points=points,
            values=values,
            grid_lon=grid_lon,
            grid_lat=grid_lat,
            power=2.0,
            max_distance=0.35,  # 最大影响距离0.35度（约35公里）
            use_adaptive_distance=True,  # 启用自适应距离
            apply_smoothing=True,  # 启用平滑处理
            smoothing_sigma=1.2  # 平滑强度
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
            grid_metadata, rainfall_grid, grid_lon, grid_lat, duration
        )
        
        logger.info("降雨栅格数据生成成功")
        
        return geojson_data
    
    def get_rainfall_at_point(
        self,
        longitude: float,
        latitude: float,
        query_time: datetime,
        duration: int = 12
    ) -> Optional[Dict[str, Any]]:
        """
        查询指定点位的降雨量（使用IDW插值）
        
        Args:
            longitude: 经度
            latitude: 纬度
            query_time: 查询时间（自动查询前12小时或24小时数据）
            duration: 持续时间（12或24小时）
            
        Returns:
            点位降雨量信息
        """
        # 获取站点数据（自动查询前12小时或24小时数据）
        stations_data = self.get_stations_data(query_time, duration)
        
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
            "level": self._get_rainfall_level(rainfall_value, duration),
            "color": InterpolationService.get_rainfall_color(rainfall_value, duration),
            "station_count": len(stations_data),
            "query_time": query_time.isoformat(),
            "duration": duration
        }
    
    @staticmethod
    def _get_rainfall_level(rainfall: float, duration: int = 12) -> str:
        """
        获取降雨等级（按照国标）
        
        Args:
            rainfall: 降雨量(mm)
            duration: 持续时间（12或24小时）
            
        Returns:
            降雨等级字符串
        """
        if duration == 12:
            # 12小时降雨等级标准
            if rainfall < 0.1:
                return "微量降雨"
            elif rainfall < 5.0:
                return "小雨"
            elif rainfall < 15.0:
                return "中雨"
            elif rainfall < 30.0:
                return "大雨"
            elif rainfall < 70.0:
                return "暴雨"
            elif rainfall < 140.0:
                return "大暴雨"
            else:
                return "特大暴雨"
        else:  # 24小时
            # 24小时降雨等级标准
            if rainfall < 0.1:
                return "微量降雨"
            elif rainfall < 10.0:
                return "小雨"
            elif rainfall < 25.0:
                return "中雨"
            elif rainfall < 50.0:
                return "大雨"
            elif rainfall < 100.0:
                return "暴雨"
            elif rainfall < 250.0:
                return "大暴雨"
            else:
                return "特大暴雨"
