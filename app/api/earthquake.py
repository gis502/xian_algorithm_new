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
            id=r["source_id"],  # 使用 source_id（隐患点/风险点ID）而非 xian_risk_factors.id
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
                  epicenter_lon: float, epicenter_lat: float) -> tuple:
    """
    同步执行地震预测（在线程池中运行）

    Returns:
        (预测结果列表, 原始结果)
    """
    points = _fetch_points(point_ids, region_code)
    if not points:
        return [], []

    model = get_earthquake_model()
    raw_results = model.predict_multiple_points(
        points,
        magnitude=magnitude,
        depth=depth,
        epicenter_lon=epicenter_lon,
        epicenter_lat=epicenter_lat,
    )
    items = _build_prediction_items(raw_results)

    save_results = [
        {
            "point_id": r.get("source_id"),  # 使用 source_id（隐患点/风险点ID）而非 xian_risk_factors.id
            "source_type": r.get("source_type"),
            "lon": r.get("lon"),
            "lat": r.get("lat"),
            "disaster_probabilities": r.get("disaster_probabilities", {}),
            "disaster_levels": r.get("disaster_levels", {})
        }
        for r in raw_results
    ]

    return items, save_results


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
    - **occurred_time**: 地震发生时间
    - **operation_type**: 操作类型（如 '实时监测', '情景模拟', '应急评估'）
    """
    semaphore = get_prediction_semaphore()

    async with semaphore:
        loop = asyncio.get_event_loop()
        try:
            items, save_results = await loop.run_in_executor(
                None, _predict_sync, req.point_ids, req.region_code,
                req.magnitude, req.depth, req.epicenter_lon, req.epicenter_lat
            )
        except Exception as e:
            logger.error(f"地震预测失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"预测失败: {e}")

    # 保存推理结果
    record_id = None
    if save_results:
        try:
            condition = {
                "point_ids": req.point_ids,
                "region_code": req.region_code,
                "magnitude": req.magnitude,
                "depth": req.depth,
                "epicenter_lon": req.epicenter_lon,
                "epicenter_lat": req.epicenter_lat
            }
            record_id = dbn_repository.save_inference_result(
                event_type="earthquake",
                occurred_time=req.occurred_time,
                operation_type=req.operation_type,
                condition=condition,
                result=save_results
            )
            logger.info(f"推理结果已保存，record_id={record_id}")
        except Exception as e:
            logger.error(f"保存推理结果失败: {e}", exc_info=True)

    return PredictResponse(code=200, message="success", data=items, record_id=record_id)
