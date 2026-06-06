"""
地震灾害链预测接口
"""
import asyncio
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException

from app.schemas.api_schemas import EarthquakePredictRequest, PredictResponse, PredictionItem
from app.utils.api_deps import get_earthquake_model, get_prediction_semaphore
from app.repositories.dbn_repository import dbn_repository
from app.config.paths import get_logger

router = APIRouter(prefix="/earthquake", tags=["地震灾害链"])
logger = get_logger("api.earthquake")

SOURCE_TYPE_MAP = {1: "隐患点", 2: "风险点"}
LEVEL_MAP = {"低": "低", "中": "中", "较高": "较高", "高": "高"}


def _build_prediction_items(results: List[Dict[str, Any]]) -> List[PredictionItem]:
    """将模型原始结果转换为接口返回格式"""
    items = []
    for r in results:
        probs = r.get("disaster_probabilities", {})
        levels = r.get("disaster_levels", {})

        if not probs:
            continue

        max_hazard = max(probs, key=probs.get)
        items.append(PredictionItem(
            id=r["point_id"],
            type=SOURCE_TYPE_MAP.get(r.get("source_type"), "未知"),
            probability=round(probs[max_hazard], 4),
            level=LEVEL_MAP.get(levels.get(max_hazard, "none"), "无"),
        ))
    return items


def _fetch_points(point_ids: Optional[List[int]], region_code: Optional[str]) -> List[Dict[str, Any]]:
    """获取点位列表"""
    if point_ids:
        return dbn_repository.get_points_by_ids(point_ids)
    return dbn_repository.get_all_points(region_code)


def _predict_sync(point_ids: Optional[List[int]], region_code: Optional[str],
                  magnitude: float, depth: float,
                  epicenter_lon: float, epicenter_lat: float) -> List[PredictionItem]:
    """同步执行地震预测（在线程池中运行）"""
    points = _fetch_points(point_ids, region_code)
    if not points:
        return []

    model = get_earthquake_model()
    results = model.predict_multiple_points(
        points,
        magnitude=magnitude,
        depth=depth,
        epicenter_lon=epicenter_lon,
        epicenter_lat=epicenter_lat,
    )
    return _build_prediction_items(results)


@router.post("/predict", response_model=PredictResponse, summary="地震灾害链预测")
async def predict_earthquake(req: EarthquakePredictRequest):
    """
    根据震级、震源深度和震中位置，批量预测隐患点/风险点的次生灾害概率和等级。

    - **point_ids**: 点位ID列表（可选，不传则查询所有点）
    - **region_code**: 行政区划代码（可选，不传则不限区域）
    - **magnitude**: 震级(Richter)
    - **depth**: 震源深度(km)，默认10km
    - **epicenter_lon**: 震中经度
    - **epicenter_lat**: 震中纬度
    """
    semaphore = get_prediction_semaphore()

    async with semaphore:
        loop = asyncio.get_event_loop()
        try:
            items = await loop.run_in_executor(
                None, _predict_sync, req.point_ids, req.region_code,
                req.magnitude, req.depth, req.epicenter_lon, req.epicenter_lat
            )
        except Exception as e:
            logger.error(f"地震预测失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"预测失败: {e}")

    return PredictResponse(code=200, message="success", data=items)
