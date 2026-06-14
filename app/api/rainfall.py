"""
暴雨灾害链预测接口
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException

from app.schemas.api_schemas import RainfallPredictRequest, PredictResponse, PredictData, UpdateMonitoringTimeRequest
from app.utils.api_deps import get_rainfall_model, get_prediction_semaphore
from app.repositories.dbn_repository import dbn_repository
from app.core.rainfall_manager import rainfall_manager
from app.config.paths import get_logger
from app.utils.time_converter import TimeConverter

router = APIRouter(prefix="/rainfall", tags=["暴雨灾害链"])
logger = get_logger("api.rainfall")

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
                  rainfall: Optional[float], duration: Optional[float],
                  operation_type: str, occurred_time: Optional[datetime] = None) -> tuple:
    """
    同步执行暴雨预测（在线程池中运行）

    Args:
        occurred_time: 事件发生时间，用于查询降雨数据和DBN推理

    Returns:
        (结果map, 传入的条件, 实际使用的事件时间)
    """
    points = _fetch_points(point_ids, region_code)
    if not points:
        return {}, {}, occurred_time or datetime.now()

    # 使用传入的时间或当前时间作为查询时间
    query_time = occurred_time or datetime.now()

    model = get_rainfall_model()
    raw_results = model.predict_multiple_points(points, rainfall=rainfall, duration=duration, query_time=query_time)
    result_map = _build_prediction_map(raw_results)

    # 存储传入的原始条件（降雨量和持续时间可能每个点不同，所以存储传入值）
    condition = {
        "point_ids": point_ids,
        "region_code": region_code,
        "rainfall": rainfall,
        "duration": duration,
        "occurred_time": query_time.isoformat() if hasattr(query_time, 'isoformat') else str(query_time)
    }

    return result_map, condition, query_time


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
    根据降雨量和持续时间，批量预测隐患点/风险点的灾害概率。

    - **disaster_name**: 灾害名称
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
            result_map, condition, occurred_time = await loop.run_in_executor(
                None, _predict_sync, req.point_ids, req.region_code,
                req.rainfall, req.duration, req.operation_type, req.occurred_time
            )
        except Exception as e:
            logger.error(f"暴雨预测失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"预测失败: {e}")

    # 保存推理结果
    record_id = None
    if result_map:
        try:
            record_id = dbn_repository.save_inference_result(
                disaster_name=req.disaster_name,
                event_type="rainfall",
                occurred_time=occurred_time,
                operation_type=req.operation_type,
                condition=condition,
                result=result_map
            )
            logger.info(f"推理结果已保存，record_id={record_id}")
        except Exception as e:
            logger.error(f"保存推理结果失败: {e}", exc_info=True)

    return PredictResponse(code=200, message="success", data=PredictData(record_id=record_id, list=result_map))
