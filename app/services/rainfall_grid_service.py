"""
降雨栅格服务
负责降雨插值、边缘优化、PNG生成等业务逻辑
"""
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from io import BytesIO

import numpy as np
from scipy.spatial import Delaunay, ConvexHull
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

from config import settings
from app.utils.logger import get_logger
from app.utils.redis_helper import redis_helper


class RainfallGridService:
    """降雨栅格服务"""
    
    def __init__(self):
        """初始化服务"""
        self.logger = get_logger()
        
        # 国标12小时累计降雨量等级和颜色映射
        self.rainfall_levels = {
            'levels': [0, 0.1, 5, 15, 30, 70, 140],
            'colors': [
                (255, 255, 255, 0),      # 无雨 - 透明
                (176, 224, 230, 255),    # 小雨 (0.1-5mm) - 淡蓝色
                (70, 130, 180, 255),     # 中雨 (5-15mm) - 钢蓝色
                (0, 0, 255, 255),        # 大雨 (15-30mm) - 蓝色
                (0, 255, 0, 255),        # 暴雨 (30-70mm) - 绿色
                (255, 255, 0, 255),      # 大暴雨 (70-140mm) - 黄色
                (255, 0, 0, 255),      # 特大暴雨 (140m+) - 红色
            ],
            'labels': ['无雨', '小雨', '中雨', '大雨', '暴雨', '大暴雨', '特大暴雨']
        }
        
        # 西安地区大致边界（用于栅格范围）
        self.xian_bounds = {
            'min_lon': 107,
            'max_lon': 110,
            'min_lat': 33,
            'max_lat': 35,
        }
        
        # 栅格分辨率（度）
        self.grid_resolution = 0.01  # 约1km
    
    def _create_buffer_points(self, points_array: np.ndarray) -> np.ndarray:
        """
        创建缓冲点：在原始站点外围生成虚拟点以扩展插值区域
        
        Args:
            points_array: 原始站点坐标数组
            
        Returns:
            缓冲点坐标数组
        """
        # 计算站点分布的中心
        center = np.mean(points_array, axis=0)
        
        # 在站点外围生成缓冲点（沿着各个方向扩展）
        buffer_points = []
        num_angles = 120  # 每隔3度生成一个缓冲点
        
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
    
    def _calculate_adaptive_max_distance(
        self,
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
        return float(np.clip(adaptive_distance, min_distance, max_distance))
    
    def interpolate_rainfall(self, station_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        使用优化的反距离权重法（IDW）进行降雨插值
        改进：
        1. 高斯核衰减替代简单幂律
        2. 自适应距离阈值
        3. 边缘渐变处理
        4. 高斯平滑减少突变
        
        Args:
            station_data: 站点数据列表
            
        Returns:
            插值结果字典
        """
        # 提取站点坐标和降雨量
        points_array = np.array([[s['lon'], s['lat']] for s in station_data])
        values_array = np.array([s['rainfall'] for s in station_data])
        
        # 创建栅格网格
        lon_range = np.arange(
            self.xian_bounds['min_lon'],
            self.xian_bounds['max_lon'],
            self.grid_resolution
        )
        lat_range = np.arange(
            self.xian_bounds['min_lat'],
            self.xian_bounds['max_lat'],
            self.grid_resolution
        )
        
        grid_lon, grid_lat = np.meshgrid(lon_range, lat_range)
        result = np.full_like(grid_lon, np.nan)
        
        # 自适应计算最大距离
        actual_max_distance = self._calculate_adaptive_max_distance(points_array)
        self.logger.info(f"使用最大影响距离: {actual_max_distance:.3f} 度")
        
        # 计算站点的凸包（带边缘缓冲）
        hull_mask = None
        confidence_mask = None
        if len(points_array) >= 3:
            try:
                # 创建缓冲站点：在原始站点外围添加虚拟点
                buffer_points = self._create_buffer_points(points_array)
                
                # 合并原始站点和缓冲站点
                all_points = np.vstack([points_array, buffer_points])
                
                # 计算凸包
                hull = ConvexHull(all_points)
                hull_points = all_points[hull.vertices]
                tri = Delaunay(hull_points)
                
                # 向量化判断所有网格点是否在凸包内
                grid_points = np.column_stack([grid_lon.ravel(), grid_lat.ravel()])
                hull_indices = tri.find_simplex(grid_points)
                hull_mask = hull_indices >= 0
                hull_mask = hull_mask.reshape(grid_lon.shape)
                
                # 计算置信度：基于到最近站点的距离
                from scipy.spatial import distance_matrix
                grid_valid = grid_points[hull_mask.ravel()]
                if len(grid_valid) > 0:
                    dist_to_stations = distance_matrix(grid_valid, points_array)
                    min_distances = np.min(dist_to_stations, axis=1)
                    
                    # 创建置信度掩码（距离越远，置信度越低）
                    confidence = np.ones(len(grid_points))
                    confidence[hull_mask.ravel()] = np.exp(-min_distances / actual_max_distance)
                    confidence_mask = confidence.reshape(grid_lon.shape)
                else:
                    confidence_mask = np.ones_like(grid_lon)
                    
            except Exception as e:
                self.logger.warning(f"凸包计算失败: {e}，使用全区域插值")
                hull_mask = np.ones_like(grid_lon, dtype=bool)
                confidence_mask = np.ones_like(grid_lon)
        else:
            hull_mask = np.ones_like(grid_lon, dtype=bool)
            confidence_mask = np.ones_like(grid_lon)
        
        # 向量化计算所有网格点到所有站点的距离
        lon_diff = grid_lon[:, :, np.newaxis] - points_array[np.newaxis, np.newaxis, :, 0]
        lat_diff = grid_lat[:, :, np.newaxis] - points_array[np.newaxis, np.newaxis, :, 1]
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
        power = 2.0
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
        
        # 计算基础插值结果
        with np.errstate(divide='ignore', invalid='ignore'):
            result = np.where(
                final_mask & (weight_total > 0),
                weighted_sum / weight_total,
                np.nan
            )
        
        # 应用置信度调整：边缘区域向邻近值渐变
        if confidence_mask is not None:
            valid_rainfall = result[final_mask]
            if len(valid_rainfall) > 0:
                mean_rainfall = np.mean(valid_rainfall)
                # 根据置信度调整结果，低置信度区域向均值靠拢
                adjusted_result = result * confidence_mask + mean_rainfall * (1 - confidence_mask)
                result = np.where(final_mask, adjusted_result, np.nan)
        
        # 应用高斯平滑减少边缘突变
        result = gaussian_filter(result, sigma=1.0)
        
        # 处理NaN值
        result = np.nan_to_num(result, nan=0.0)
        
        return {
            'grid_values': result,
            'grid_lon': grid_lon,
            'grid_lat': grid_lat,
            'lon_range': lon_range,
            'lat_range': lat_range,
        }
    
    def optimize_edges(self, grid_data: Dict[str, Any], 
                      station_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        优化栅格边缘（已在插值时处理，此方法保留用于向后兼容）
        
        Args:
            grid_data: 插值结果
            station_data: 站点数据
            
        Returns:
            优化后的栅格数据
        """
        # 由于interpolate_rainfall已经包含了边缘优化和平滑处理
        # 这里不再重复处理，直接返回
        return grid_data
    
    def save_rainfall_grid_png(self, grid_data: Dict[str, Any], max_id: int) -> Optional[str]:
        """
        将降雨栅格保存为PNG图片（背景透明）
        
        Args:
            grid_data: 栅格数据
            max_id: 最大ID
            
        Returns:
            PNG文件相对路径，失败返回None
        """
        try:
            grid_values = grid_data['grid_values']
            lon_range = grid_data['lon_range']
            lat_range = grid_data['lat_range']
            
            # 创建自定义颜色映射
            levels = self.rainfall_levels['levels']
            colors = self.rainfall_levels['colors']
            
            cmap = ListedColormap([
                tuple(c / 255.0 for c in color) for color in colors
            ])
            
            norm = BoundaryNorm(levels, cmap.N)
            
            # 创建图形（设置dpi确保不拉伸）
            fig, ax = plt.subplots(1, 1, figsize=(10, 10), dpi=100)
            
            # 绘制栅格
            im = ax.pcolormesh(
                lon_range,
                lat_range,
                grid_values,
                cmap=cmap,
                norm=norm,
                shading='auto'
            )
            
            # 设置透明背景
            fig.patch.set_alpha(0)
            ax.patch.set_alpha(0)
            
            # 移除坐标轴
            ax.set_axis_off()
            
            # 调整布局，去除白边
            plt.tight_layout(pad=0)
            
            # 构建文件路径
            file_store_dir = settings.FILE_STORE_DIR
            grid_dir_template = settings.RAIN_STATION_GRID_DIR
            
            # 替换:id为实际的max_id
            grid_dir = grid_dir_template.replace(':id', str(max_id))
            
            # 完整路径
            full_dir = os.path.join(file_store_dir, grid_dir.lstrip('/'))
            
            # 创建目录
            os.makedirs(full_dir, exist_ok=True)
            
            # 保存PNG（使用PIL确保透明度）
            png_path = os.path.join(full_dir, 'grid.png')
            
            # 先保存到缓冲区
            buf = BytesIO()
            plt.savefig(buf, format='png', transparent=True, bbox_inches='tight', pad_inches=0)
            buf.seek(0)
            
            # 使用PIL打开并重新保存，确保透明度正确
            img = Image.open(buf)
            img.save(png_path, 'PNG')
            
            buf.close()
            plt.close(fig)
            
            # 返回相对路径（相对于FILE_STORE_DIR），统一使用正斜杠
            relative_path = os.path.join(grid_dir, 'grid.png').replace('\\', '/')
            
            self.logger.info(f"PNG图片已保存: {png_path.replace('\\', '/')}")
            return relative_path
            
        except Exception as e:
            self.logger.error(f"保存PNG图片失败: {e}", exc_info=True)
            return None
    
    def store_to_redis(self, png_path: str, max_id: int, 
                      query_time, station_data: List[Dict[str, Any]]):
        """
        将栅格信息存储到Redis
        
        Args:
            png_path: PNG文件相对路径
            max_id: 最大ID
            query_time: 查询时间（datetime对象或字符串）
            station_data: 站点数据
        """
        try:
            redis_key = settings.REDIS_RAIN_STATION_GRID_KEY
            
            # 处理query_time，可能是datetime对象或字符串
            if isinstance(query_time, datetime):
                query_time_str = query_time.isoformat()
            else:
                query_time_str = str(query_time)
            
            # 构建辅助前端定位的信息
            grid_info = {
                'id': max_id,
                'png_path': png_path,  # 相对路径
                'query_time': query_time_str,
                'resolution': self.grid_resolution,  # 分辨率
                'station_count': len(station_data),  # 站点数量
                # Cesium需要的定位信息
                'cesium_config': {
                    'rectangle': {
                        'west': self.xian_bounds['min_lon'],
                        'south': self.xian_bounds['min_lat'],
                        'east': self.xian_bounds['max_lon'],
                        'north': self.xian_bounds['max_lat'],
                    },
                    # 图片尺寸（需要读取实际图片）
                    'width': int((self.xian_bounds['max_lon'] - self.xian_bounds['min_lon']) / self.grid_resolution),
                    'height': int((self.xian_bounds['max_lat'] - self.xian_bounds['min_lat']) / self.grid_resolution),
                }
            }
            
            # 存储到Redis
            redis_helper.set(redis_key, json.dumps(grid_info))
            
            self.logger.info(f"栅格信息已存储到Redis，key: {redis_key}, id: {max_id}")
            
        except Exception as e:
            self.logger.error(f"存储到Redis失败: {e}", exc_info=True)


# 创建全局实例
rainfall_grid_service = RainfallGridService()
