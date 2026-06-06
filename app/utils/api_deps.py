"""
API 依赖注入
模型懒加载 + 并发控制
"""
import asyncio
from typing import Optional

from app.config.paths import get_logger

logger = get_logger("api")

# ============================================================
# 并发控制：限制同时进行的预测任务数，防止资源耗尽
# ============================================================
MAX_CONCURRENT_PREDICTIONS = 8
_prediction_semaphore: Optional[asyncio.Semaphore] = None


def get_prediction_semaphore() -> asyncio.Semaphore:
    """获取预测信号量（惰性初始化，兼容事件循环）"""
    global _prediction_semaphore
    if _prediction_semaphore is None:
        _prediction_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PREDICTIONS)
    return _prediction_semaphore


# ============================================================
# 模型单例（启动时加载一次）
# ============================================================
_rainfall_model = None
_earthquake_model = None


def get_rainfall_model():
    """获取暴雨DBN模型单例"""
    global _rainfall_model
    if _rainfall_model is None:
        from app.models.dbn.rainfall.rainfall_dbn import RainfallDBN
        _rainfall_model = RainfallDBN()
        logger.info("暴雨DBN模型加载完成")
    return _rainfall_model


def get_earthquake_model():
    """获取地震DBN模型单例"""
    global _earthquake_model
    if _earthquake_model is None:
        from app.models.dbn.earthquake.earthquake_dbn import EarthquakeDBN
        _earthquake_model = EarthquakeDBN()
        logger.info("地震DBN模型加载完成")
    return _earthquake_model


def is_model_loaded() -> dict:
    """检查模型加载状态"""
    return {
        "rainfall_model_loaded": _rainfall_model is not None,
        "earthquake_model_loaded": _earthquake_model is not None,
    }
