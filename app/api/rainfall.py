"""
暴雨灾害链预测接口
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException

from app.schemas.api_schemas import RainfallPredictRequest, PredictResponse, PredictionItem, UpdateMonitoringTimeRequest
from app.utils.api_deps import get_rainfall_model, get_prediction_semaphore
from app.repositories.dbn_repository import dbn_repository
from app.core.rainfall_manager import rainfall_manager
from app.config.paths import get_logger
from app.utils.time_converter import TimeConverter

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
                  rainfall: Optional[float], duration: Optional[float],
                  operation_type: str) -> tuple:
    """
    同步执行暴雨预测（在线程池中运行）

    Returns:
        (预测结果列表, 原始结果, 输入条件, 当前时间)
    """
    points = _fetch_points(point_ids, region_code)
    if not points:
        return [], [], {}, datetime.now()

    model = get_rainfall_model()
    raw_results = model.predict_multiple_points(points, rainfall=rainfall, duration=duration)
    items = _build_prediction_items(raw_results)

    # 构建条件和结果用于保存
    now = datetime.now()
    condition = {
        "point_ids": point_ids,
        "region_code": region_code,
        "rainfall": rainfall,
        "duration": duration
    }
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

    return items, save_results, condition, now


@router.post("/update-monitoring-time", summary="更新降雨监测查询时间")
async def update_monitoring_time(req: UpdateMonitoringTimeRequest):
    """
    更新降雨站点监测的查询时间，触发重新计算
    
    - **query_time**: 新的查询时间，格式: YYYY-MM-DD HH:mm:ss
    """
    try:
        # 将字符串时间解析为 datetime 对象
        new_time = TimeConverter.parse_input_time(req.query_time)
        
        # 更新监测时间，触发重新计算
        result = rainfall_manager.update_query_time(new_time)
        
        logger.info(f"更新监测时间成功: {result}")
        return {
            "code": 200,
            "message": "success",
            "data": result
        }
    except ValueError as e:
        logger.error(f"时间格式错误: {e}")
        raise HTTPException(status_code=400, detail=f"时间格式错误: {e}")
    except Exception as e:
        logger.error(f"更新监测时间失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新监测时间失败: {e}")


@router.post("/predict", response_model=PredictResponse, summary="暴雨灾害链预测")
async def predict_rainfall(req: RainfallPredictRequest):
    """
    根据降雨量和持续时间，批量预测隐患点/风险点的灾害概率和等级。

    - **point_ids**: 点位ID列表（可选，不传则查询所有点）
    - **region_code**: 行政区划代码（可选，不传则不限区域）
    - **rainfall**: 累计降雨量(mm)，不传则从气象表自动获取
    - **duration**: 降雨持续时间(h)，不传则从气象表自动获取
    - **operation_type**: 操作类型（如 '实时监测', '情景模拟', '应急评估'）
    """
    semaphore = get_prediction_semaphore()

    async with semaphore:
        loop = asyncio.get_event_loop()
        try:
            items, save_results, condition, now = await loop.run_in_executor(
                None, _predict_sync, req.point_ids, req.region_code,
                req.rainfall, req.duration, req.operation_type
            )
        except Exception as e:
            logger.error(f"暴雨预测失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"预测失败: {e}")

    # 保存推理结果
    record_id = None
    if save_results:
        try:
            record_id = dbn_repository.save_inference_result(
                event_type="rainfall",
                occurred_time=now,
                operation_type=req.operation_type,
                condition=condition,
                result=save_results
            )
            logger.info(f"推理结果已保存，record_id={record_id}")
        except Exception as e:
            logger.error(f"保存推理结果失败: {e}", exc_info=True)

    return PredictResponse(code=200, message="success", data=items, record_id=record_id)
