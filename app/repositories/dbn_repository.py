"""
数据库查询模块
负责从 xian_risk_factors、xian_meteorology 等表获取数据
"""
import math
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.utils.db_helper import db_helper
from app.config.paths import get_logger

logger = get_logger("dbn")


class DbnRepository:
    """数据库查询类 - 所有DBN相关查询统一管理"""

    # ==================== 风险因子查询 ====================

    @staticmethod
    def get_all_points(region_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取所有隐患点和风险点（从 xian_risk_factors 表）

        Args:
            region_code: 行政区划代码（区县名称），可选

        Returns:
            点列表，每个元素包含：id, source_id, source_type, lon, lat, static_factors
        """
        sql = """
            SELECT
                id,
                source_id,
                source_type,
                lon,
                lat,
                static_factors
            FROM xian_risk_factors
            WHERE is_delete = 0
        """
        params = (region_code,) if region_code else None

        if region_code:
            sql += " AND county = %s"

        results = db_helper.execute_query(sql, params)

        points = []
        for row in results:
            points.append({
                'id': row['id'],
                'source_id': row['source_id'],
                'source_type': row['source_type'],
                'lon': float(row['lon']) if row['lon'] else None,
                'lat': float(row['lat']) if row['lat'] else None,
                'static_factors': row.get('static_factors') or {}
            })

        return points

    @staticmethod
    def get_point_by_id(point_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取单个点信息

        Args:
            point_id: xian_risk_factors 表的 ID

        Returns:
            点信息
        """
        sql = """
            SELECT
                rf.id,
                rf.source_id,
                rf.source_type,
                rf.lon,
                rf.lat,
                rf.static_factors
            FROM xian_risk_factors rf
            WHERE rf.id = %s AND rf.is_delete = 0
        """
        result = db_helper.execute_query_one(sql, (point_id,))

        if not result:
            return None

        return {
            'id': result['id'],
            'source_id': result['source_id'],
            'source_type': result['source_type'],
            'lon': float(result['lon']) if result['lon'] else None,
            'lat': float(result['lat']) if result['lat'] else None,
            'static_factors': result.get('static_factors') or {}
        }

    @staticmethod
    def get_static_factors(point_id: int) -> Dict[str, Any]:
        """
        获取点的静态因子数据

        Args:
            point_id: xian_risk_factors 表的 ID

        Returns:
            静态因子数据
        """
        sql = """
            SELECT static_factors
            FROM xian_risk_factors
            WHERE id = %s AND is_delete = 0
        """
        result = db_helper.execute_query_one(sql, (point_id,))

        if result and result.get('static_factors'):
            return result['static_factors']
        return {}

    # ==================== 降雨数据查询 ====================

    @staticmethod
    def get_nearest_station_rainfall(lon: float, lat: float,
                                     query_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        获取最近雨量站的降雨数据

        Args:
            lon: 经度
            lat: 纬度
            query_time: 查询时间，若未提供则取当前时间

        Returns:
            降雨数据
        """
        if query_time is None:
            query_time = datetime.now()

        # noinspection SqlNoDataSourceInspection
        sql = """
            WITH station_data AS (
                SELECT
                    lon,
                    lat,
                    SUM(CAST(rainfall_1h AS DOUBLE PRECISION)) as total_rainfall,
                    COUNT(*) as record_count
                FROM xian_meteorology
                WHERE datetime BETWEEN
                    CAST(EXTRACT(EPOCH FROM (%s::timestamp - INTERVAL '24 hours')) AS BIGINT)
                    AND CAST(EXTRACT(EPOCH FROM %s::timestamp) AS BIGINT)
                    AND rainfall_1h IS NOT NULL
                    AND CAST(rainfall_1h AS DOUBLE PRECISION) > 0
                GROUP BY lon, lat
            )
            SELECT
                lon,
                lat,
                total_rainfall,
                record_count,
                ST_DistanceSphere(
                    ST_SetSRID(ST_MakePoint(lon, lat), 4326),
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                ) as distance
            FROM station_data
            ORDER BY distance
            LIMIT 1
        """
        result = db_helper.execute_query_one(sql, (query_time, query_time, lon, lat))

        if result:
            return {
                'rainfall': float(result['total_rainfall']) if result['total_rainfall'] else 0.0,
                'record_count': int(result['record_count']) if result['record_count'] else 0,
                'distance': float(result['distance']) if result['distance'] else 0.0,
                'station_lon': float(result['lon']) if result['lon'] else None,
                'station_lat': float(result['lat']) if result['lat'] else None
            }
        else:
            return {
                'rainfall': 0.0,
                'record_count': 0,
                'distance': 0.0,
                'station_lon': None,
                'station_lat': None
            }

    @staticmethod
    def get_rainfall_data_with_duration(lon: float, lat: float,
                                        query_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        获取降雨数据，包括累计降雨量和持续时间

        Args:
            lon: 经度
            lat: 纬度
            query_time: 查询时间，若未提供则取当前时间

        Returns:
            降雨数据：{accum_rain, duration_hours, rain_intensity}
        """
        if query_time is None:
            query_time = datetime.now()

        # 查找最近的雨量站
        # noinspection SqlNoDataSourceInspection
        sql = """
            SELECT lon, lat, dist
            FROM (
                SELECT DISTINCT lon, lat,
                    ST_DistanceSphere(
                        ST_SetSRID(ST_MakePoint(lon, lat), 4326),
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                    ) as dist
                FROM xian_meteorology
            ) t
            WHERE dist < 50000
            ORDER BY dist
            LIMIT 1
        """
        station = db_helper.execute_query_one(sql, (lon, lat))

        if not station:
            return {'accum_rain': 0.0, 'duration_hours': 0, 'rain_intensity': 0.0}

        station_lon = station['lon']
        station_lat = station['lat']

        # 查询该站点的降雨时序数据
        # noinspection SqlNoDataSourceInspection
        sql = """
            SELECT
                datetime,
                CAST(rainfall_1h AS DOUBLE PRECISION) as rainfall
            FROM xian_meteorology
            WHERE lon = %s AND lat = %s
            AND datetime BETWEEN
                CAST(EXTRACT(EPOCH FROM (%s::timestamp - INTERVAL '72 hours')) AS BIGINT)
                AND CAST(EXTRACT(EPOCH FROM %s::timestamp) AS BIGINT)
            ORDER BY datetime DESC
        """
        results = db_helper.execute_query(sql, (station_lon, station_lat, query_time, query_time))

        if not results:
            return {'accum_rain': 0.0, 'duration_hours': 0, 'rain_intensity': 0.0}

        # 计算累计降雨量和持续时间
        accum_rain = 0.0
        duration_hours = 0
        consecutive_no_rain = 0

        for row in results:
            rainfall = float(row['rainfall']) if row['rainfall'] else 0.0
            if rainfall > 0:
                accum_rain += rainfall
                duration_hours += 1
                consecutive_no_rain = 0
            else:
                consecutive_no_rain += 1
                if consecutive_no_rain >= 3:
                    break
                if accum_rain > 0:
                    duration_hours += 1

        rain_intensity = accum_rain / duration_hours if duration_hours > 0 else 0.0

        return {
            'accum_rain': accum_rain,
            'duration_hours': duration_hours,
            'rain_intensity': rain_intensity
        }

    # ==================== 空间查询 ====================

    @staticmethod
    def get_nearest_station(lon: float, lat: float,
                            station_type: str = 'meteorology') -> Optional[Dict[str, Any]]:
        """
        获取最近的气象站点

        Args:
            lon: 经度
            lat: 纬度
            station_type: 站点类型

        Returns:
            最近站点信息
        """
        sql = """
            SELECT DISTINCT ON (lon, lat)
                lon,
                lat,
                ST_DistanceSphere(
                    ST_SetSRID(ST_MakePoint(lon, lat), 4326),
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                ) as distance
            FROM xian_meteorology
            WHERE is_delete = 0
            ORDER BY lon, lat, distance
            LIMIT 1
        """

        result = db_helper.execute_query_one(sql, (lon, lat))

        if result:
            return {
                'lon': float(result['lon']),
                'lat': float(result['lat']),
                'distance': float(result['distance'])
            }
        return None

    @staticmethod
    def get_distance_to_river(lon: float, lat: float) -> float:
        """
        计算点到最近河流的距离

        Args:
            lon: 经度
            lat: 纬度

        Returns:
            距离（米）
        """
        sql = """
            SELECT
                MIN(ST_DistanceSphere(
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    geom
                )) as min_distance
            FROM xian_rivers
            WHERE is_delete = 0
        """

        result = db_helper.execute_query_one(sql, (lon, lat))

        if result and result['min_distance']:
            return float(result['min_distance'])
        return 0.0

    @staticmethod
    def get_distance_to_fault(lon: float, lat: float) -> float:
        """
        计算点到最近断裂带的距离

        Args:
            lon: 经度
            lat: 纬度

        Returns:
            距离（米）
        """
        sql = """
            SELECT
                MIN(ST_DistanceSphere(
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    geom
                )) as min_distance
            FROM xian_fault_lines
            WHERE is_delete = 0
        """

        result = db_helper.execute_query_one(sql, (lon, lat))

        if result and result['min_distance']:
            return float(result['min_distance'])
        return 0.0

    @staticmethod
    def get_pipe_density(lon: float, lat: float, buffer_radius: float = 500.0) -> float:
        """
        计算点周围缓冲区内的管网密度

        Args:
            lon: 经度
            lat: 纬度
            buffer_radius: 缓冲区半径（米）

        Returns:
            管网密度（m/m²）
        """
        sql = """
            SELECT
                COALESCE(SUM(ST_Length(wp.geom::geography)), 0) as total_length
            FROM xian_water_pipe wp
            WHERE wp.is_delete = 0
            AND ST_DWithin(
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                wp.geom::geography,
                %s
            )
        """

        result = db_helper.execute_query_one(sql, (lon, lat, buffer_radius))

        if result and result['total_length']:
            total_length = float(result['total_length'])
            buffer_area = math.pi * buffer_radius ** 2
            density = total_length / buffer_area
            return density
        return 0.0

    @staticmethod
    def get_river_density(lon: float, lat: float, buffer_radius: float = 1000.0) -> float:
        """
        计算点周围缓冲区内的河流密度

        Args:
            lon: 经度
            lat: 纬度
            buffer_radius: 缓冲区半径（米）

        Returns:
            河流密度（m/m²）
        """
        sql = """
            SELECT
                COALESCE(SUM(ST_Length(r.geom::geography)), 0) as total_length
            FROM xian_rivers r
            WHERE r.is_delete = 0
            AND ST_DWithin(
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                r.geom::geography,
                %s
            )
        """

        result = db_helper.execute_query_one(sql, (lon, lat, buffer_radius))

        if result and result['total_length']:
            total_length = float(result['total_length'])
            buffer_area = math.pi * buffer_radius ** 2
            density = total_length / buffer_area
            return density
        return 0.0

    @staticmethod
    def get_point_elevation(lon: float, lat: float) -> Optional[float]:
        """
        获取点的高程值

        Args:
            lon: 经度
            lat: 纬度

        Returns:
            高程值（米）
        """
        sql = """
            SELECT
                ST_Value(rast, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) as elevation
            FROM xian_dem
            WHERE ST_Intersects(rast, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
            LIMIT 1
        """

        result = db_helper.execute_query_one(sql, (lon, lat, lon, lat))

        if result and result['elevation']:
            return float(result['elevation'])
        return None

    @staticmethod
    def get_point_slope(lon: float, lat: float) -> Optional[float]:
        """
        获取点的坡度值

        Args:
            lon: 经度
            lat: 纬度

        Returns:
            坡度值（度）
        """
        sql = """
            SELECT
                ST_Value(rast, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) as slope
            FROM xian_slope
            WHERE ST_Intersects(rast, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
            LIMIT 1
        """

        result = db_helper.execute_query_one(sql, (lon, lat, lon, lat))

        if result and result['slope']:
            return float(result['slope'])
        return None

    @staticmethod
    def get_point_aspect(lon: float, lat: float) -> Optional[float]:
        """
        获取点的坡向值

        Args:
            lon: 经度
            lat: 纬度

        Returns:
            坡向值（度）
        """
        sql = """
            SELECT
                ST_Value(rast, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) as aspect
            FROM xian_aspect
            WHERE ST_Intersects(rast, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
            LIMIT 1
        """

        result = db_helper.execute_query_one(sql, (lon, lat, lon, lat))

        if result and result['aspect']:
            return float(result['aspect'])
        return None


# 创建全局实例
dbn_repository = DbnRepository()
