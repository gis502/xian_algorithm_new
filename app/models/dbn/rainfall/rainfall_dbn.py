"""
暴雨灾害链DBN模型
实现贝叶斯网络推理，预测5类灾害概率
"""
import os
import yaml
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.utils.discretizer import discretizer
from app.repositories.dbn_repository import DbnRepository
from app.config.paths import DBN_CONFIG_DIR, get_logger

logger = get_logger("dbn")


class RainfallDBN:
    """暴雨灾害链DBN模型"""

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
        初始化DBN模型

        Args:
            config_dir: 配置文件目录
        """
        if config_dir is None:
            config_dir = str(DBN_CONFIG_DIR)

        self.config_dir = config_dir
        self.graph_config = self._load_graph_config()
        self.cpt_config = self._load_cpt_config()

        # 构建贝叶斯网络结构
        self._build_network()

    def _load_graph_config(self) -> Dict[str, Any]:
        """加载图结构配置"""
        config_path = os.path.join(self.config_dir, 'rainfall_dbn_graph.yaml')

        if not os.path.exists(config_path):
            logger.error(f"图结构配置文件不存在: {config_path}")
            return {}

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return config

    def _load_cpt_config(self) -> Dict[str, Any]:
        """加载CPT配置"""
        config_path = os.path.join(self.config_dir, 'rainfall_cpt_params.yaml')

        if not os.path.exists(config_path):
            logger.error(f"CPT配置文件不存在: {config_path}")
            return {}

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return config

    def _build_network(self):
        """构建贝叶斯网络结构"""
        # 获取节点列表
        self.trigger_nodes = self.graph_config.get('layers', {}).get('trigger', [])
        self.environment_nodes = self.graph_config.get('layers', {}).get('environment', [])
        self.hazard_nodes = self.graph_config.get('layers', {}).get('hazard', [])

        # 获取所有节点
        self.all_nodes = self.trigger_nodes + self.environment_nodes + self.hazard_nodes

        # 获取边关系
        self.edges = self.graph_config.get('edges', [])

        # 获取节点状态
        self.node_states = self.graph_config.get('node_states', {})

        # 构建父子关系
        self.children = {node: [] for node in self.all_nodes}
        self.parents = {node: [] for node in self.all_nodes}

        for parent, child in self.edges:
            if parent in self.all_nodes and child in self.all_nodes:
                self.children[parent].append(child)
                self.parents[child].append(parent)

        # 构建CPT表
        self._build_cpt_tables()

    def _build_cpt_tables(self):
        """构建条件概率表"""
        self.cpt_tables = {}

        for node in self.all_nodes:
            if node in self.cpt_config:
                self.cpt_tables[node] = self.cpt_config[node]
            else:
                # 如果没有配置，使用均匀分布
                states = self.node_states.get(node, ['no', 'yes'])
                if len(states) == 2:
                    # 二值节点
                    self.cpt_tables[node] = {
                        'type': 'prior',
                        'probabilities': [0.5, 0.5]
                    }
                else:
                    # 多值节点
                    prob = 1.0 / len(states)
                    self.cpt_tables[node] = {
                        'type': 'prior',
                        'probabilities': [prob] * len(states)
                    }

    def _get_node_probability(self, node: str, evidence: Dict[str, str]) -> List[float]:
        """
        获取节点的概率分布

        Args:
            node: 节点名称
            evidence: 证据字典

        Returns:
            概率分布列表
        """
        cpt = self.cpt_tables.get(node)
        if not cpt:
            states = self.node_states.get(node, ['no', 'yes'])
            return [1.0 / len(states)] * len(states)

        # 如果是先验概率
        if cpt.get('type') == 'prior':
            return cpt.get('probabilities', [0.5, 0.5])

        # 如果是条件概率
        if cpt.get('type') == 'conditional':
            return self._evaluate_conditional_probability(node, cpt, evidence)

        return [0.5, 0.5]

    def _evaluate_conditional_probability(self, node: str, cpt: Dict[str, Any],
                                          evidence: Dict[str, str]) -> List[float]:
        """
        评估条件概率

        Args:
            node: 节点名称
            cpt: CPT配置
            evidence: 证据字典

        Returns:
            概率分布列表
        """
        states = self.node_states.get(node, ['no', 'yes'])
        default_prob = cpt.get('default_probability', 0.05)

        # 检查规则
        rules = cpt.get('rules', [])
        for rule in rules:
            condition = rule.get('condition', {})
            probability = rule.get('probability', default_prob)

            # 检查是否满足条件
            if self._check_condition(condition, evidence):
                # 返回 [P(no), P(yes)]
                return [1.0 - probability, probability]

        # 如果没有匹配的规则，返回默认概率
        return [1.0 - default_prob, default_prob]

    def _check_condition(self, condition: Dict[str, Any], evidence: Dict[str, str]) -> bool:
        """
        检查条件是否满足

        Args:
            condition: 条件字典
            evidence: 证据字典

        Returns:
            是否满足
        """
        for node, required_states in condition.items():
            if node not in evidence:
                return False

            evidence_state = evidence[node]

            # 如果required_states是列表，检查是否在列表中
            if isinstance(required_states, list):
                if evidence_state not in required_states:
                    return False
            else:
                # 如果是单个值，检查是否相等
                if evidence_state != required_states:
                    return False

        return True

    def predict_single_point(self, point: Dict[str, Any],
                             rainfall: Optional[float] = None,
                             duration: Optional[float] = None,
                             query_time: Optional[datetime] = None,
                             rainfall_data_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        对单个点进行预测

        Args:
            point: 点信息（包含 static_factors 字段）
            rainfall: 累计降雨量（可选）
            duration: 持续时间（可选）
            query_time: 查询时间（可选）
            rainfall_data_override: 预取的降雨数据（批量模式下避免重复查询）

        Returns:
            预测结果
        """
        point_id = point.get('id')
        lon = point.get('lon')
        lat = point.get('lat')
        source_type = point.get('source_type')

        logger.info(f"预测点 ID={point_id}, source_type={source_type}")

        # 获取降雨数据
        if rainfall is not None and duration is not None:
            rain_intensity = rainfall / duration if duration > 0 else 0.0
            rainfall_data = {
                'accum_rain': rainfall,
                'duration_hours': duration,
                'rain_intensity': rain_intensity
            }
        elif rainfall_data_override is not None:
            rainfall_data = rainfall_data_override
        else:
            rainfall_data = DbnRepository.get_rainfall_data_with_duration(lon, lat, query_time)

        # 获取静态因子数据（从 point 的 static_factors 字段）
        raw_factors = point.get('static_factors', {})
        static_factors = {
            'elevation': raw_factors.get('dem_value'),
            'slope': raw_factors.get('slope_value'),
            'aspect': raw_factors.get('aspect_value'),
            'soil_type': raw_factors.get('soil_type'),
            'lithology': raw_factors.get('lithology'),
            'landuse': raw_factors.get('landuse'),
            'terrain': raw_factors.get('landform'),
            'impervious': raw_factors.get('impervious_surface'),
            'ndvi': raw_factors.get('vegetation_index'),
            'sand_content': raw_factors.get('soil_sand'),
            'ph': raw_factors.get('soil_ph'),
            'soil_moisture': raw_factors.get('soil_moisture'),
            'organic_carbon': raw_factors.get('organic_carbon'),
            'dist_to_river': raw_factors.get('river_distance'),
            'dist_to_fault': raw_factors.get('fault_distance'),
            'pipe_density': raw_factors.get('pipe_density')
        }

        # 合并所有因子
        all_factors = {
            'rain_intensity': rainfall_data.get('rain_intensity', 0.0),
            'duration': rainfall_data.get('duration_hours', 0),
            'accum_rain': rainfall_data.get('accum_rain', 0.0),
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
            'disaster_probabilities': {
                h: r['probability'] for h, r in hazard_results.items()
            },
            'disaster_levels': {
                h: r['level'] for h, r in hazard_results.items()
            }
        }

        return result

    def _run_inference(self, evidence: Dict[str, str]) -> Dict[str, Any]:
        """
        运行贝叶斯推理

        Args:
            evidence: 证据字典

        Returns:
            灾害概率字典，每个值包含 probability 和 level
        """
        hazard_probabilities = {}

        for hazard_node in self.hazard_nodes:
            # 获取灾害节点的概率
            prob_dist = self._get_node_probability(hazard_node, evidence)

            # 取发生概率（第二个状态）
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
                rainfall: Optional[float] = None,
                duration: Optional[float] = None,
                timestamp: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        预测灾害概率

        Args:
            region_code: 行政区划代码（可选）
            rainfall: 累计降雨量（可选，全局值）
            duration: 持续时间（可选，全局值）
            timestamp: 时间（可选）

        Returns:
            预测结果列表
        """
        # 1. 获取点列表
        points = DbnRepository.get_all_points(region_code)

        if not points:
            logger.warning(f"没有找到点数据，region_code={region_code}")
            return []

        logger.info(f"共找到 {len(points)} 个点")

        # 2. 对每个点进行预测
        results = []
        for point in points:
            try:
                result = self.predict_single_point(
                    point,
                    rainfall=rainfall,
                    duration=duration,
                    query_time=timestamp
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
                                rainfall: Optional[float] = None,
                                duration: Optional[float] = None,
                                query_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        对已获取的点列表进行暴雨灾害预测

        Args:
            points: 点信息列表（已从数据库获取）
            rainfall: 累计降雨量（可选）
            duration: 持续时间（可选）
            query_time: 查询时间（可选）

        Returns:
            预测结果列表
        """
        # 批量预取降雨数据（避免逐点N+1查询）
        batch_rainfall: Optional[Dict[str, Dict[str, Any]]] = None
        if (rainfall is None or duration is None) and points:
            batch_points = [
                {'id': p.get('id'), 'lon': p.get('lon'), 'lat': p.get('lat')}
                for p in points
            ]
            batch_rainfall = DbnRepository.get_rainfall_data_batch(batch_points, query_time)
            logger.info(f"批量预取降雨数据完成，覆盖 {len(batch_rainfall)} 个点")

        results = []
        for point in points:
            try:
                point_id = point.get('id')
                override = batch_rainfall.get(point_id) if batch_rainfall else None
                result = self.predict_single_point(
                    point, rainfall=rainfall, duration=duration,
                    query_time=query_time, rainfall_data_override=override
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
        """
        获取模型信息

        Returns:
            模型信息字典
        """
        return {
            'trigger_nodes': self.trigger_nodes,
            'environment_nodes': self.environment_nodes,
            'hazard_nodes': self.hazard_nodes,
            'edges': self.edges,
            'node_states': self.node_states
        }


# 创建全局实例
rainfall_dbn = RainfallDBN()
