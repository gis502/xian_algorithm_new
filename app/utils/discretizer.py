"""
离散化模块
负责将连续值转换为离散状态
"""
import os
import yaml
from typing import Optional, List, Dict, Any, Tuple
from app.config.paths import DBN_CONFIG_DIR, get_logger

logger = get_logger("dbn")


class Discretizer:
    """离散化工具类"""

    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化离散化器

        Args:
            config_dir: 配置文件目录，默认为 app/config/dbn
        """
        if config_dir is None:
            config_dir = str(DBN_CONFIG_DIR)

        self.config_dir = config_dir
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载离散化配置"""
        config_path = os.path.join(self.config_dir, 'discretization.yaml')
        
        if not os.path.exists(config_path):
            logger.warning(f"离散化配置文件不存在: {config_path}")
            return {}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config

    def discretize(self, factor_name: str, value: float, 
                   region_code: Optional[str] = None) -> str:
        """
        将连续值离散化

        Args:
            factor_name: 因子名称
            value: 连续值
            region_code: 行政区划代码，用于区域覆盖

        Returns:
            离散状态标签
        """
        if factor_name not in self.config:
            logger.warning(f"因子 {factor_name} 没有离散化配置")
            return "unknown"

        factor_config = self.config[factor_name]

        # 检查是否是分类变量（有mapping字段）
        if 'mapping' in factor_config:
            return self._discretize_categorical(factor_config, value)

        # 检查是否有区域覆盖
        if region_code and 'region_overrides' in factor_config:
            if region_code in factor_config['region_overrides']:
                override_config = factor_config['region_overrides'][region_code]
                return self._discretize_continuous(override_config, value)

        # 使用默认配置
        if 'default' in factor_config:
            return self._discretize_continuous(factor_config['default'], value)
        elif 'bins' in factor_config:
            return self._discretize_continuous(factor_config, value)

        logger.warning(f"因子 {factor_name} 的配置格式不正确")
        return "unknown"

    def _discretize_categorical(self, config: Dict[str, Any], value: float) -> str:
        """
        离散化分类变量

        Args:
            config: 配置
            value: 值

        Returns:
            离散状态标签
        """
        mapping = config.get('mapping', {})
        default = config.get('default', 'unknown')
        
        # 将值转换为整数
        int_value = int(value)
        
        return mapping.get(int_value, default)

    def _discretize_continuous(self, config: Dict[str, Any], value: float) -> str:
        """
        离散化连续变量

        Args:
            config: 配置
            value: 值

        Returns:
            离散状态标签
        """
        bins = config.get('bins', [])
        labels = config.get('labels', [])

        if not bins or not labels:
            logger.warning("离散化配置缺少bins或labels")
            return "unknown"

        # 确保bins和labels长度匹配
        if len(bins) != len(labels) + 1:
            logger.warning(f"bins长度({len(bins)})应该比labels长度({len(labels)})多1")
            return "unknown"

        # 进行分箱
        for i in range(len(bins) - 1):
            if bins[i] <= value < bins[i + 1]:
                return labels[i]

        # 如果值超出范围，返回最后一个标签
        if value >= bins[-1]:
            return labels[-1]

        return labels[0]

    def discretize_rain_intensity(self, rainfall_mm_h: float) -> str:
        """
        离散化降雨强度

        Args:
            rainfall_mm_h: 降雨强度（mm/h）

        Returns:
            离散状态标签
        """
        return self.discretize('rain_intensity', rainfall_mm_h)

    def discretize_duration(self, duration_hours: float) -> str:
        """
        离散化持续时间

        Args:
            duration_hours: 持续时间（小时）

        Returns:
            离散状态标签
        """
        return self.discretize('duration', duration_hours)

    def discretize_accum_rain(self, accum_rain_mm: float) -> str:
        """
        离散化累计降雨量

        Args:
            accum_rain_mm: 累计降雨量（mm）

        Returns:
            离散状态标签
        """
        return self.discretize('accum_rain', accum_rain_mm)

    # ---- 地震触发层离散化 ----

    def discretize_magnitude(self, magnitude: float) -> str:
        """
        离散化地震震级

        Args:
            magnitude: 震级（Richter）

        Returns:
            离散状态标签
        """
        return self.discretize('magnitude', magnitude)

    def discretize_epicenter_distance(self, distance_km: float) -> str:
        """
        离散化震中距

        Args:
            distance_km: 震中距（km）

        Returns:
            离散状态标签
        """
        return self.discretize('epicenter_distance', distance_km)

    def discretize_seismic_intensity(self, intensity: float) -> str:
        """
        离散化地震烈度

        Args:
            intensity: 地震烈度（中国烈度表数值）

        Returns:
            离散状态标签
        """
        return self.discretize('seismic_intensity', intensity)

    def discretize_elevation(self, elevation_m: float, 
                             region_code: Optional[str] = None) -> str:
        """
        离散化高程

        Args:
            elevation_m: 高程（米）
            region_code: 行政区划代码

        Returns:
            离散状态标签
        """
        return self.discretize('elevation', elevation_m, region_code)

    def discretize_slope(self, slope_deg: float) -> str:
        """
        离散化坡度

        Args:
            slope_deg: 坡度（度）

        Returns:
            离散状态标签
        """
        return self.discretize('slope', slope_deg)

    def discretize_aspect(self, aspect_deg: float) -> str:
        """
        离散化坡向

        Args:
            aspect_deg: 坡向（度）

        Returns:
            离散状态标签
        """
        return self.discretize('aspect', aspect_deg)

    def discretize_soil_type(self, soil_type_code: int) -> str:
        """
        离散化土壤类型

        Args:
            soil_type_code: 土壤类型代码

        Returns:
            离散状态标签
        """
        return self.discretize('soil_type', soil_type_code)

    def discretize_lithology(self, lithology_code: int) -> str:
        """
        离散化岩性

        Args:
            lithology_code: 岩性代码

        Returns:
            离散状态标签
        """
        return self.discretize('lithology', lithology_code)

    def discretize_landuse(self, landuse_code: int) -> str:
        """
        离散化土地利用类型

        Args:
            landuse_code: 土地利用类型代码

        Returns:
            离散状态标签
        """
        return self.discretize('landuse', landuse_code)

    def discretize_terrain(self, terrain_code: int) -> str:
        """
        离散化地形分类

        Args:
            terrain_code: 地形分类代码

        Returns:
            离散状态标签
        """
        return self.discretize('terrain', terrain_code)

    def discretize_impervious(self, impervious_ratio: float) -> str:
        """
        离散化不透水面

        Args:
            impervious_ratio: 不透水面比例

        Returns:
            离散状态标签
        """
        return self.discretize('impervious', impervious_ratio)

    def discretize_ndvi(self, ndvi_value: float) -> str:
        """
        离散化植被指数

        Args:
            ndvi_value: NDVI值

        Returns:
            离散状态标签
        """
        return self.discretize('ndvi', ndvi_value)

    def discretize_sand_content(self, sand_percent: float) -> str:
        """
        离散化土壤含沙量

        Args:
            sand_percent: 含沙量百分比

        Returns:
            离散状态标签
        """
        return self.discretize('sand_content', sand_percent)

    def discretize_ph(self, ph_value: float) -> str:
        """
        离散化土壤PH值

        Args:
            ph_value: PH值

        Returns:
            离散状态标签
        """
        return self.discretize('ph', ph_value)

    def discretize_soil_moisture(self, moisture_percent: float) -> str:
        """
        离散化土壤湿度

        Args:
            moisture_percent: 湿度百分比

        Returns:
            离散状态标签
        """
        return self.discretize('soil_moisture', moisture_percent)

    def discretize_organic_carbon(self, carbon_percent: float) -> str:
        """
        离散化有机碳

        Args:
            carbon_percent: 有机碳百分比

        Returns:
            离散状态标签
        """
        return self.discretize('organic_carbon', carbon_percent)

    def discretize_dist_to_river(self, distance_m: float) -> str:
        """
        离散化距离河道距离

        Args:
            distance_m: 距离（米）

        Returns:
            离散状态标签
        """
        return self.discretize('dist_to_river', distance_m)

    def discretize_dist_to_fault(self, distance_m: float) -> str:
        """
        离散化距离断裂带距离

        Args:
            distance_m: 距离（米）

        Returns:
            离散状态标签
        """
        return self.discretize('dist_to_fault', distance_m)

    def discretize_pipe_density(self, density: float,
                                region_code: Optional[str] = None) -> str:
        """
        离散化供水管网密度

        Args:
            density: 管网密度（m/m²）
            region_code: 行政区划代码

        Returns:
            离散状态标签
        """
        return self.discretize('pipe_density', density, region_code)

    def discretize_all_factors(self, factors: Dict[str, Any], 
                               region_code: Optional[str] = None) -> Dict[str, str]:
        """
        离散化所有因子

        Args:
            factors: 因子字典，key为因子名称，value为连续值
            region_code: 行政区划代码

        Returns:
            离散化后的因子字典
        """
        result = {}

        # 暴雨触发层
        if 'rain_intensity' in factors:
            result['rain_intensity'] = self.discretize_rain_intensity(factors['rain_intensity'])
        if 'duration' in factors:
            result['duration'] = self.discretize_duration(factors['duration'])
        if 'accum_rain' in factors:
            result['accum_rain'] = self.discretize_accum_rain(factors['accum_rain'])

        # 地震触发层
        if 'magnitude' in factors:
            result['magnitude'] = self.discretize_magnitude(factors['magnitude'])
        if 'epicenter_distance' in factors:
            result['epicenter_distance'] = self.discretize_epicenter_distance(factors['epicenter_distance'])
        if 'seismic_intensity' in factors:
            result['seismic_intensity'] = self.discretize_seismic_intensity(factors['seismic_intensity'])

        # 环境层
        if 'elevation' in factors:
            result['elevation'] = self.discretize_elevation(factors['elevation'], region_code)
        if 'slope' in factors:
            result['slope'] = self.discretize_slope(factors['slope'])
        if 'aspect' in factors:
            result['aspect'] = self.discretize_aspect(factors['aspect'])
        if 'soil_type' in factors:
            result['soil_type'] = self.discretize_soil_type(factors['soil_type'])
        if 'lithology' in factors:
            result['lithology'] = self.discretize_lithology(factors['lithology'])
        if 'landuse' in factors:
            result['landuse'] = self.discretize_landuse(factors['landuse'])
        if 'terrain' in factors:
            result['terrain'] = self.discretize_terrain(factors['terrain'])
        if 'impervious' in factors:
            result['impervious'] = self.discretize_impervious(factors['impervious'])
        if 'ndvi' in factors:
            result['ndvi'] = self.discretize_ndvi(factors['ndvi'])
        if 'sand_content' in factors:
            result['sand_content'] = self.discretize_sand_content(factors['sand_content'])
        if 'ph' in factors:
            result['ph'] = self.discretize_ph(factors['ph'])
        if 'soil_moisture' in factors:
            result['soil_moisture'] = self.discretize_soil_moisture(factors['soil_moisture'])
        if 'organic_carbon' in factors:
            result['organic_carbon'] = self.discretize_organic_carbon(factors['organic_carbon'])
        if 'dist_to_river' in factors:
            result['dist_to_river'] = self.discretize_dist_to_river(factors['dist_to_river'])
        if 'dist_to_fault' in factors:
            result['dist_to_fault'] = self.discretize_dist_to_fault(factors['dist_to_fault'])
        if 'pipe_density' in factors:
            result['pipe_density'] = self.discretize_pipe_density(factors['pipe_density'], region_code)

        return result


# 创建全局实例
discretizer = Discretizer()
