"""
暴雨灾害链预测接口
"""
import asyncio
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException

from app.schemas.api_schemas import RainfallPredictRequest, PredictResponse, PredictionItem
from app.utils.api_deps import get_rainfall_model, get_prediction_semaphore
from app.repositories.dbn_repository import dbn_repository
from app.config.paths import get_logger

router = APIRouter(prefix="/rainfall", tags=["暴雨灾害链"])
logger = get_logger("api.rainfall")

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
                  rainfall: float, duration: float) -> List[PredictionItem]:
    """同步执行暴雨预测（在线程池中运行）"""
    points = _fetch_points(point_ids, region_code)
    if not points:
        return []

    model = get_rainfall_model()
    results = model.predict_multiple_points(points, rainfall=rainfall, duration=duration)
    return _build_prediction_items(results)


@router.post("/predict", response_model=PredictResponse, summary="暴雨灾害链预测")
async def predict_rainfall(req: RainfallPredictRequest):
    """
    根据降雨量和持续时间，批量预测隐患点/风险点的灾害概率和等级。

    - **point_ids**: 点位ID列表（可选，不传则查询所有点）
    - **region_code**: 行政区划代码（可选，不传则不限区域）
    - **rainfall**: 累计降雨量(mm)
    - **duration**: 降雨持续时间(h)
    """
    semaphore = get_prediction_semaphore()

    async with semaphore:
        loop = asyncio.get_event_loop()
        try:
            items = await loop.run_in_executor(
                None, _predict_sync, req.point_ids, req.region_code,
                req.rainfall, req.duration
            )
        except Exception as e:
            logger.error(f"暴雨预测失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"预测失败: {e}")

    return PredictResponse(code=200, message="success", data=items)
