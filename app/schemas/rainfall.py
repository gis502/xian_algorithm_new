"""
降雨数据相关的Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class RainfallGridRequest(BaseModel):
    """降雨栅格请求模型"""
    time: Optional[str] = Field(
        None, 
        alias="time",
        description="查询时间 ISO格式，默认为当前时间（自动查询前12小时或24小时数据）", 
        example="2024-01-01T12:00:00"
    )
    resolution: float = Field(
        0.01, 
        alias="resolution",
        description="栅格分辨率（度）", 
        gt=0, 
        le=0.1
    )
    duration: int = Field(
        12, 
        alias="duration",
        description="持续时间（小时），可选12或24", 
        ge=12, 
        le=24
    )
    
    class Config:
        populate_by_name = True  # 允许同时使用字段名和别名


class StationData(BaseModel):
    """站点数据模型"""
    lon: float
    lat: float
    rainfall: float


class GridMetadata(BaseModel):
    """栅格元数据"""
    start_time: str
    end_time: str
    district_id: int
    resolution: float
    station_count: int
    grid_size: List[int]
    bounds: dict


class RainfallGridResponse(BaseModel):
    """降雨栅格响应模型 - 符合前端 ApiResponse 结构"""
    code: int = Field(200, description="状态码")
    message: str = Field(..., description="响应消息")
    data: Optional[dict] = Field(None, description="响应数据")


class StationsResponse(BaseModel):
    """站点数据响应模型 - 符合前端 ApiResponse 结构"""
    code: int = Field(200, description="状态码")
    message: str = Field(..., description="响应消息")
    data: List[StationData] = Field(default_factory=list, description="站点数据列表")
