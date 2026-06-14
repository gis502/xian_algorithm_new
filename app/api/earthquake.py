"""
地震灾害链预测接口
"""
import asyncio
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException

from app.schemas.api_schemas import EarthquakePredictRequest, PredictResponse, PredictData
from app.utils.api_deps import get_earthquake_model, get_prediction_semaphore
from app.repositories.dbn_repository import dbn_repository
from app.config.paths import get_logger

router = APIRouter(prefix="/earthquake", tags=["地震灾害链"])
logger = get_logger("api.earthquake")

SOURCE_TYPE_MAP = {1: "隐患点", 2: "风险点"}
LEVEL_MAP = {"低": "低", "中": "中", "较高": "较高", "高": "高"}


def _build_prediction_map(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """将模型原始结果转换为存储格式: {id_type: 概率百分比}"""
    result_map = {}
    for r in results:
        probs = r.get("disaster_probabilities", {})
        if not probs:
            continue

        source_id = r["source_id"]
        source_type = r.get("source_type")
        max_hazard = max(probs, key=probs.get)
        # key 格式: {source_id}_{source_type}，value 为百分比概率
        key = f"{source_id}_{source_type}"
        result_map[key] = round(probs[max_hazard] * 100, 2)
    return result_map


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
        (结果map,)
    """
    points = _fetch_points(point_ids, region_code)
    if not points:
        return {}

    model = get_earthquake_model()
    raw_results = model.predict_multiple_points(
        points,
        magnitude=magnitude,
        depth=depth,
        epicenter_lon=epicenter_lon,
        epicenter_lat=epicenter_lat,
    )
    result_map = _build_prediction_map(raw_results)

    return result_map


@router.post("/predict", response_model=PredictResponse, summary="地震灾害链预测")
async def predict_earthquake(req: EarthquakePredictRequest):
    """
    根据震级、震源深度和震中位置，批量预测隐患点/风险点的次生灾害概率。

    - **disaster_name**: 灾害名称
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
            result_map = await loop.run_in_executor(
                None, _predict_sync, req.point_ids, req.region_code,
                req.magnitude, req.depth, req.epicenter_lon, req.epicenter_lat
            )
        except Exception as e:
            logger.error(f"地震预测失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"预测失败: {e}")

    # 保存推理结果
    record_id = None
    if result_map:
        try:
            # 使用传入的 occurred_time，如果未传则使用当前时间
            from datetime import datetime
            occurred_time = req.occurred_time if req.occurred_time else datetime.now()
            # 存储经过默认值处理的条件
            condition = {
                "point_ids": req.point_ids,
                "region_code": req.region_code,
                "magnitude": req.magnitude,
                "depth": req.depth,  # 已有默认值 10.0
                "epicenter_lon": req.epicenter_lon,
                "epicenter_lat": req.epicenter_lat,
                "occurred_time": occurred_time.isoformat() if hasattr(occurred_time, 'isoformat') else str(occurred_time)
            }
            record_id = dbn_repository.save_inference_result(
                disaster_name=req.disaster_name,
                event_type="earthquake",
                occurred_time=occurred_time,
                operation_type=req.operation_type,
                condition=condition,
                result=result_map
            )
            logger.info(f"推理结果已保存，record_id={record_id}")
        except Exception as e:
            logger.error(f"保存推理结果失败: {e}", exc_info=True)

    return PredictResponse(code=200, message="success", data=PredictData(record_id=record_id, list=result_map))
