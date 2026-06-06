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
            region_code: 行政区划代码（如 '610104'），可选，匹配隐患点.county_code 和风险点.unit_code

        Returns:
            点列表，每个元素包含：id, source_id, source_type, lon, lat, static_factors
        """
        if region_code:
            # 通过源表的行政区划代码筛选
            sql = """
                SELECT rf.id, rf.source_id, rf.source_type, rf.lon, rf.lat, rf.static_factors
                FROM xian_risk_factors rf
                WHERE rf.is_delete = 0
                  AND (
                    (rf.source_type = 1 AND rf.source_id IN (
                        SELECT id FROM xian_hidden_danger_spots WHERE county_id = %s AND is_delete = 0
                    ))
                    OR
                    (rf.source_type = 2 AND rf.source_id IN (
                        SELECT id FROM xian_risk_spots WHERE unit_code = %s AND is_delete = 0
                    ))
                  )
            """
            params = (region_code, region_code)
        else:
            sql = """
                SELECT id, source_id, source_type, lon, lat, static_factors
                FROM xian_risk_factors
                WHERE is_delete = 0
            """
            params = None

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
    def get_points_by_ids(point_ids: List[int]) -> List[Dict[str, Any]]:
        """
        批量获取点信息

        Args:
            point_ids: 点ID列表

        Returns:
            点信息列表
        """
        if not point_ids:
            return []

        placeholders = ','.join(['%s'] * len(point_ids))
        sql = f"""
            SELECT
                rf.id,
                rf.source_id,
                rf.source_type,
                rf.lon,
                rf.lat,
                rf.static_factors
            FROM xian_risk_factors rf
            WHERE rf.id IN ({placeholders}) AND rf.is_delete = 0
        """
        results = db_helper.execute_query(sql, tuple(point_ids))

        return [{
            'id': row['id'],
            'source_id': row['source_id'],
            'source_type': row['source_type'],
            'lon': float(row['lon']) if row['lon'] else None,
            'lat': float(row['lat']) if row['lat'] else None,
            'static_factors': row.get('static_factors') or {}
        } for row in results]

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

    # ---- 批量降雨查询（性能优化） ----

    _cached_stations: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def _ensure_stations_cached(cls) -> List[Dict[str, Any]]:
        """一次性加载所有气象站点坐标到内存（188个站点，约2KB）"""
        if cls._cached_stations is not None:
            return cls._cached_stations
        sql = "SELECT DISTINCT lon, lat FROM xian_meteorology"
        cls._cached_stations = db_helper.execute_query(sql)
        logger.info(f"已缓存 {len(cls._cached_stations)} 个气象站点坐标")
        return cls._cached_stations

    @staticmethod
    def _haversine_distance(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """Haversine公式计算两点间距离（米）"""
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @classmethod
    def _find_nearest_station(cls, lon: float, lat: float) -> Optional[Dict[str, Any]]:
        """在缓存的站点中找最近的一个（纯Python，微秒级）"""
        stations = cls._ensure_stations_cached()
        if not stations:
            return None
        best = None
        best_dist = float('inf')
        for s in stations:
            d = cls._haversine_distance(lon, lat, s['lon'], s['lat'])
            if d < best_dist:
                best_dist = d
                best = s
        if best_dist > 50000:
            return None
        return {'lon': best['lon'], 'lat': best['lat'], 'dist': best_dist}

    @classmethod
    def get_rainfall_data_batch(cls, points: List[Dict[str, Any]],
                                query_time: Optional[datetime] = None) -> Dict[str, Dict[str, Any]]:
        """
        批量获取多个点的降雨数据（2次DB查询替代 N×2次）

        Args:
            points: 预测点列表，每个含 {'id': str, 'lon': float, 'lat': float}
            query_time: 查询时间

        Returns:
            {point_id: {accum_rain, duration_hours, rain_intensity}}
        """
        if query_time is None:
            query_time = datetime.now()

        # 结果模板（无数据时的默认值）
        default = {'accum_rain': 0.0, 'duration_hours': 0, 'rain_intensity': 0.0}
        result: Dict[str, Dict[str, Any]] = {}

        # 1. 为每个点找最近站点（纯Python，瞬间完成）
        station_to_points: Dict[tuple, List[str]] = {}
        for p in points:
            station = cls._find_nearest_station(p['lon'], p['lat'])
            if station is None:
                result[p['id']] = default.copy()
                continue
            key = (station['lon'], station['lat'])
            station_to_points.setdefault(key, []).append(p['id'])

        if not station_to_points:
            return result

        # 2. 一次批量查所有站点的72小时降雨数据
        station_keys = list(station_to_points.keys())
        placeholders = ', '.join(['(%s, %s)'] * len(station_keys))
        params: List[Any] = []
        for slon, slat in station_keys:
            params.extend([slon, slat])
        params.extend([query_time, query_time])

        # noinspection SqlNoDataSourceInspection
        sql = f"""
            SELECT lon, lat, datetime, CAST(rainfall_1h AS DOUBLE PRECISION) as rainfall
            FROM xian_meteorology
            WHERE (lon, lat) IN ({placeholders})
            AND datetime BETWEEN
                CAST(EXTRACT(EPOCH FROM (%s::timestamp - INTERVAL '72 hours')) AS BIGINT)
                AND CAST(EXTRACT(EPOCH FROM %s::timestamp) AS BIGINT)
            ORDER BY lon, lat, datetime DESC
        """
        rows = db_helper.execute_query(sql, tuple(params))

        # 3. 按站点分组，计算累计降雨量和持续时间
        from itertools import groupby
        station_rainfall: Dict[tuple, Dict[str, Any]] = {}
        for (slon, slat), group in groupby(rows, key=lambda r: (r['lon'], r['lat'])):
            accum_rain = 0.0
            duration_hours = 0
            consecutive_no_rain = 0
            for row in group:
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
            intensity = accum_rain / duration_hours if duration_hours > 0 else 0.0
            station_rainfall[(slon, slat)] = {
                'accum_rain': accum_rain,
                'duration_hours': duration_hours,
                'rain_intensity': intensity
            }

        # 4. 分发给各预测点
        for (slon, slat), point_ids in station_to_points.items():
            rain_data = station_rainfall.get((slon, slat), default)
            for pid in point_ids:
                result[pid] = rain_data

        return result

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
