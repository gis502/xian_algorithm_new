"""
API 请求/响应数据模型
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ============================================================
# 暴雨预测
# ============================================================

class RainfallPredictRequest(BaseModel):
    """暴雨灾害链预测请求"""
    point_ids: Optional[List[int]] = Field(None, max_length=500,
                                           description="点位ID列表，不传则查询所有点")
    region_code: Optional[str] = Field(None, description="行政区划代码（如 '610104'），不传则不限区域")
    rainfall: Optional[float] = Field(None, ge=0,
                                       description="累计降雨量(mm)，不传则从气象表自动获取")
    duration: Optional[float] = Field(None, ge=0,
                                       description="降雨持续时间(h)，不传则从气象表自动获取")
    operation_type: str = Field("模拟", min_length=1, max_length=50,
                                description="操作类型（如 '模拟', '实时监测', '应急评估'）")


# ============================================================
# 地震预测
# ============================================================

class EarthquakePredictRequest(BaseModel):
    """地震灾害链预测请求"""
    point_ids: Optional[List[int]] = Field(None, max_length=500,
                                           description="点位ID列表，不传则查询所有点")
    region_code: Optional[str] = Field(None, description="行政区划代码（如 '610104'），不传则不限区域")
    magnitude: float = Field(..., ge=0, le=10, description="震级(Richter)")
    depth: float = Field(10.0, gt=0, le=700, description="震源深度(km)，默认10km")
    epicenter_lon: float = Field(..., ge=-180, le=180, description="震中经度")
    epicenter_lat: float = Field(..., ge=-90, le=90, description="震中纬度")
    occurred_time: datetime = Field(..., description="地震发生时间")
    operation_type: str = Field("模拟", min_length=1, max_length=50,
                                description="操作类型（如 '模拟', '实时监测', '应急评估'）")


# ============================================================
# 通用响应
# ============================================================

class PredictionItem(BaseModel):
    """单个点位预测结果"""
    id: int = Field(..., description="点位ID")
    type: str = Field(..., description="类型: 隐患点 / 风险点")
    probability: float = Field(..., description="最大灾害概率")
    level: str = Field(..., description="灾害等级: 低/中/较高/高")


class PredictResponse(BaseModel):
    """预测响应"""
    code: int = Field(200, description="状态码")
    message: str = Field("success", description="提示信息")
    data: List[PredictionItem] = Field(default_factory=list, description="预测结果列表")
    record_id: Optional[int] = Field(None, description="推理结果记录ID")


class UpdateMonitoringTimeRequest(BaseModel):
    """更新监测时间请求"""
    query_time: str = Field(..., description="查询时间，格式: YYYY-MM-DD HH:mm:ss，如 '2025-09-16 20:00:00'")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    rainfall_model_loaded: bool = False
    earthquake_model_loaded: bool = False
