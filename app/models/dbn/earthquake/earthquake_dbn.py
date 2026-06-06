"""
地震灾害链DBN模型
实现贝叶斯网络推理，预测地震触发的3类地质灾害概率：
滑坡（landslide）、泥石流（debris_flow）、崩塌（collapse）
"""
import os
import math
import yaml
from typing import Optional, List, Dict, Any

from app.utils.discretizer import discretizer
from app.repositories.dbn_repository import DbnRepository
from app.config.paths import DBN_CONFIG_DIR, get_logger

logger = get_logger("earthquake_dbn")


class EarthquakeDBN:
    """地震灾害链DBN模型"""

    # 灾害概率→等级的阈值映射
    HAZARD_LEVEL_THRESHOLDS = [
        (0.7, '高'),
        (0.5, '较高'),
        (0.3, '中'),
        (0.0, '低'),
    ]

    def _probability_to_level(self, prob: float) -> str:
        """将连续概率映射到风险等级：低(<30%) / 中(30-50%) / 较高(50-70%) / 高(70%+)"""
        for threshold, level in self.HAZARD_LEVEL_THRESHOLDS:
            if prob >= threshold:
                return level
        return '低'

    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化地震DBN模型

        Args:
            config_dir: 配置文件目录，默认为 app/config/dbn
        """
        if config_dir is None:
            config_dir = str(DBN_CONFIG_DIR)

        self.config_dir = config_dir
        self.graph_config = self._load_graph_config()
        self.cpt_config = self._load_cpt_config()

        self._build_network()

    def _load_graph_config(self) -> Dict[str, Any]:
        """加载地震图结构配置"""
        config_path = os.path.join(self.config_dir, 'earthquake_dbn_graph.yaml')

        if not os.path.exists(config_path):
            logger.error(f"地震图结构配置文件不存在: {config_path}")
            return {}

        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _load_cpt_config(self) -> Dict[str, Any]:
        """加载地震CPT配置"""
        config_path = os.path.join(self.config_dir, 'earthquake_cpt_params.yaml')

        if not os.path.exists(config_path):
            logger.error(f"地震CPT配置文件不存在: {config_path}")
            return {}

        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _build_network(self):
        """构建贝叶斯网络结构"""
        self.trigger_nodes = self.graph_config.get('layers', {}).get('trigger', [])
        self.environment_nodes = self.graph_config.get('layers', {}).get('environment', [])
        self.hazard_nodes = self.graph_config.get('layers', {}).get('hazard', [])

        self.all_nodes = self.trigger_nodes + self.environment_nodes + self.hazard_nodes
        self.edges = self.graph_config.get('edges', [])
        self.node_states = self.graph_config.get('node_states', {})

        self.children = {node: [] for node in self.all_nodes}
        self.parents = {node: [] for node in self.all_nodes}

        for parent, child in self.edges:
            if parent in self.all_nodes and child in self.all_nodes:
                self.children[parent].append(child)
                self.parents[child].append(parent)

        self._build_cpt_tables()

    def _build_cpt_tables(self):
        """构建条件概率表"""
        self.cpt_tables = {}

        for node in self.all_nodes:
            if node in self.cpt_config:
                self.cpt_tables[node] = self.cpt_config[node]
            else:
                states = self.node_states.get(node, ['no', 'yes'])
                if len(states) == 2:
                    self.cpt_tables[node] = {
                        'type': 'prior',
                        'probabilities': [0.5, 0.5]
                    }
                else:
                    prob = 1.0 / len(states)
                    self.cpt_tables[node] = {
                        'type': 'prior',
                        'probabilities': [prob] * len(states)
                    }

    @staticmethod
    def estimate_seismic_intensity(magnitude: float, epicenter_distance_km: float,
                                   depth_km: float = 10.0) -> float:
        """
        根据震级、震中距和震源深度估算地震烈度

        I = 0.923 + 1.621*M - 3.494*ln(R+10) - ln(H/10)

        参考：GB 18306-2015 中国地震动参数区划图
        深度修正：震源越深，地表烈度越低

        Args:
            magnitude: 震级（Richter）
            epicenter_distance_km: 震中距（km）
            depth_km: 震源深度（km），默认10km

        Returns:
            估算的地震烈度（中国烈度表数值）
        """
        if epicenter_distance_km < 0:
            epicenter_distance_km = 0

        intensity = 0.923 + 1.621 * magnitude - 3.494 * math.log(epicenter_distance_km + 10)

        # 震源深度修正：以10km为基准，深度越大烈度衰减越多
        depth_km = max(depth_km, 1.0)
        intensity -= math.log(depth_km / 10.0)

        # 限制在合理范围内
        return max(1.0, min(12.0, intensity))

    def _get_node_probability(self, node: str, evidence: Dict[str, str]) -> List[float]:
        """获取节点的概率分布"""
        cpt = self.cpt_tables.get(node)
        if not cpt:
            states = self.node_states.get(node, ['no', 'yes'])
            return [1.0 / len(states)] * len(states)

        if cpt.get('type') == 'prior':
            return cpt.get('probabilities', [0.5, 0.5])

        if cpt.get('type') == 'conditional':
            return self._evaluate_conditional_probability(node, cpt, evidence)

        return [0.5, 0.5]

    def _evaluate_conditional_probability(self, node: str, cpt: Dict[str, Any],
                                          evidence: Dict[str, str]) -> List[float]:
        """评估条件概率"""
        states = self.node_states.get(node, ['no', 'yes'])
        default_prob = cpt.get('default_probability', 0.02)

        rules = cpt.get('rules', [])
        for rule in rules:
            condition = rule.get('condition', {})
            probability = rule.get('probability', default_prob)

            if self._check_condition(condition, evidence):
                return [1.0 - probability, probability]

        return [1.0 - default_prob, default_prob]

    def _check_condition(self, condition: Dict[str, Any], evidence: Dict[str, str]) -> bool:
        """检查条件是否满足"""
        for node, required_states in condition.items():
            if node not in evidence:
                return False

            evidence_state = evidence[node]

            if isinstance(required_states, list):
                if evidence_state not in required_states:
                    return False
            else:
                if evidence_state != required_states:
                    return False

        return True

    def predict_single_point(self, point: Dict[str, Any],
                             magnitude: float,
                             epicenter_distance: Optional[float] = None,
                             seismic_intensity: Optional[float] = None,
                             epicenter_lon: Optional[float] = None,
                             epicenter_lat: Optional[float] = None,
                             depth: float = 10.0) -> Dict[str, Any]:
        """
        对单个点进行地震灾害预测

        Args:
            point: 点信息（包含 static_factors 字段，来自 xian_risk_factors 表）
            magnitude: 地震震级（Richter）
            epicenter_distance: 震中距（km），若未提供则通过震中坐标计算
            seismic_intensity: 地震烈度（中国烈度表），若未提供则自动估算
            epicenter_lon: 震中经度（可选，用于计算震中距）
            epicenter_lat: 震中纬度（可选，用于计算震中距）
            depth: 震源深度（km），默认10.0

        Returns:
            预测结果
        """
        point_id = point.get('id')
        lon = point.get('lon')
        lat = point.get('lat')
        source_type = point.get('source_type')

        logger.debug(f"地震预测点 ID={point_id}, source_type={source_type}")

        # 计算震中距（如果未直接提供）
        if epicenter_distance is None:
            if epicenter_lon is not None and epicenter_lat is not None:
                epicenter_distance = self._haversine_distance(
                    lon, lat, epicenter_lon, epicenter_lat
                )
            else:
                logger.warning("未提供震中距或震中坐标，使用默认值 100km")
                epicenter_distance = 100.0

        # 估算地震烈度（如果未直接提供）
        if seismic_intensity is None:
            seismic_intensity = self.estimate_seismic_intensity(magnitude, epicenter_distance, depth)

        # 获取静态因子数据
        raw_factors = point.get('static_factors', {})
        static_factors = {
            'elevation': raw_factors.get('dem_value'),
            'slope': raw_factors.get('slope_value'),
            'aspect': raw_factors.get('aspect_value'),
            'soil_type': raw_factors.get('soil_type'),
            'lithology': raw_factors.get('lithology'),
            'landuse': raw_factors.get('landuse'),
            'terrain': raw_factors.get('landform'),
            'ndvi': raw_factors.get('vegetation_index'),
            'sand_content': raw_factors.get('soil_sand'),
            'ph': raw_factors.get('soil_ph'),
            'soil_moisture': raw_factors.get('soil_moisture'),
            'organic_carbon': raw_factors.get('organic_carbon'),
            'dist_to_river': raw_factors.get('river_distance'),
            'dist_to_fault': raw_factors.get('fault_distance'),
        }

        # 合并地震触发因子和静态因子
        all_factors = {
            'magnitude': magnitude,
            'epicenter_distance': epicenter_distance,
            'seismic_intensity': seismic_intensity,
            **static_factors
        }

        # 离散化
        evidence = discretizer.discretize_all_factors(all_factors)

        # 运行推理
        hazard_results = self._run_inference(evidence)

        # 构造输出
        result = {
            'point_id': point_id,
            'source_type': source_type,
            'lon': lon,
            'lat': lat,
            'earthquake_params': {
                'magnitude': magnitude,
                'epicenter_distance': round(epicenter_distance, 1),
                'seismic_intensity': round(seismic_intensity, 1),
            },
            'disaster_probabilities': {
                h: r['probability'] for h, r in hazard_results.items()
            },
            'disaster_levels': {
                h: r['level'] for h, r in hazard_results.items()
            }
        }

        return result

    def _haversine_distance(self, lon1: float, lat1: float,
                            lon2: float, lat2: float) -> float:
        """
        使用Haversine公式计算两点间距离

        Args:
            lon1, lat1: 点1的经纬度
            lon2, lat2: 点2的经纬度

        Returns:
            距离（km）
        """
        R = 6371.0  # 地球半径（km）

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = math.sin(dlat / 2) ** 2 + \
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def _run_inference(self, evidence: Dict[str, str]) -> Dict[str, Any]:
        """运行贝叶斯推理"""
        hazard_probabilities = {}

        for hazard_node in self.hazard_nodes:
            prob_dist = self._get_node_probability(hazard_node, evidence)

            if len(prob_dist) >= 2:
                prob = prob_dist[1]
            else:
                prob = 0.0

            hazard_probabilities[hazard_node] = {
                'probability': round(prob, 4),
                'level': self._probability_to_level(prob)
            }

        return hazard_probabilities

    def predict(self, region_code: Optional[str] = None,
                magnitude: float = 6.0,
                epicenter_distance: Optional[float] = None,
                seismic_intensity: Optional[float] = None,
                epicenter_lon: Optional[float] = None,
                epicenter_lat: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        对所有点进行地震灾害预测

        Args:
            region_code: 行政区划代码（可选）
            magnitude: 地震震级（默认6.0）
            epicenter_distance: 震中距（km，可选）
            seismic_intensity: 地震烈度（可选）
            epicenter_lon: 震中经度（可选）
            epicenter_lat: 震中纬度（可选）

        Returns:
            预测结果列表
        """
        points = DbnRepository.get_all_points(region_code)

        if not points:
            logger.warning(f"没有找到点数据，region_code={region_code}")
            return []

        logger.info(f"地震灾害预测：共 {len(points)} 个点，震级 M{magnitude}")

        results = []
        for point in points:
            try:
                result = self.predict_single_point(
                    point,
                    magnitude=magnitude,
                    epicenter_distance=epicenter_distance,
                    seismic_intensity=seismic_intensity,
                    epicenter_lon=epicenter_lon,
                    epicenter_lat=epicenter_lat
                )
                results.append(result)
            except Exception as e:
                logger.error(f"预测点 {point.get('id')} 失败: {e}")
                results.append({
                    'point_id': point.get('id'),
                    'source_type': point.get('source_type'),
                    'lon': point.get('lon'),
                    'lat': point.get('lat'),
                    'error': str(e)
                })

        return results

    def predict_multiple_points(self, points: List[Dict[str, Any]],
                                magnitude: float = 6.0,
                                epicenter_distance: Optional[float] = None,
                                seismic_intensity: Optional[float] = None,
                                epicenter_lon: Optional[float] = None,
                                epicenter_lat: Optional[float] = None,
                                depth: float = 10.0) -> List[Dict[str, Any]]:
        """
        对已获取的点列表进行地震灾害预测

        Args:
            points: 点信息列表（已从数据库获取）
            magnitude: 地震震级
            epicenter_distance: 震中距（km，可选）
            seismic_intensity: 地震烈度（可选）
            epicenter_lon: 震中经度（可选）
            epicenter_lat: 震中纬度（可选）
            depth: 震源深度（km），默认10.0

        Returns:
            预测结果列表
        """
        results = []
        for point in points:
            try:
                result = self.predict_single_point(
                    point,
                    magnitude=magnitude,
                    epicenter_distance=epicenter_distance,
                    seismic_intensity=seismic_intensity,
                    epicenter_lon=epicenter_lon,
                    epicenter_lat=epicenter_lat,
                    depth=depth
                )
                results.append(result)
            except Exception as e:
                logger.error(f"预测点 {point.get('id')} 失败: {e}")
                results.append({
                    'point_id': point.get('id'),
                    'source_type': point.get('source_type'),
                    'lon': point.get('lon'),
                    'lat': point.get('lat'),
                    'error': str(e)
                })
        return results

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            'model_type': 'earthquake',
            'trigger_nodes': self.trigger_nodes,
            'environment_nodes': self.environment_nodes,
            'hazard_nodes': self.hazard_nodes,
            'edges': self.edges,
            'node_states': self.node_states
        }


# 创建全局实例
earthquake_dbn = EarthquakeDBN()
