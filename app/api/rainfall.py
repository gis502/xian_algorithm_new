"""
降雨数据API Controller - 路由层
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional

from app.services.rainfall_service import RainfallService
from app.schemas.rainfall import (
    RainfallGridRequest,
    RainfallGridResponse,
    StationsResponse
)
from app.utils.logger import setup_logging

logger = setup_logging()

router = APIRouter(
    prefix="/rainfall",
    tags=["降雨数据"],
    responses={404: {"description": "Not found"}}
)

# 创建服务实例
rainfall_service = RainfallService()


@router.post("/grid", response_model=RainfallGridResponse, summary="获取降雨栅格数据")
async def get_rainfall_grid(request: RainfallGridRequest):
    """
    获取指定时间的降雨栅格数据
    
    使用反距离权重插值(IDW)方法，将站点降雨数据插值为连续栅格，
    返回适合Cesium渲染的GeoJSON格式数据。
    
    Args:
        request: 包含时间、分辨率和持续时间的请求
        
    Returns:
        GeoJSON格式的栅格数据
    """
    try:
        # 解析时间，如果未提供则使用当前时间
        now = datetime.now()
        query_time = datetime.fromisoformat(request.time) if request.time else now
        
        # 验证duration参数
        if request.duration not in [12, 24]:
            raise ValueError("duration参数必须为12或24")
        
        # 调用服务层生成栅格（自动查询前12小时或24小时数据）
        geojson_data = rainfall_service.generate_rainfall_grid(
            query_time=query_time,
            resolution=request.resolution,
            duration=request.duration
        )
        
        if not geojson_data:
            return RainfallGridResponse(
                code=404,
                message="未找到降雨数据",
                data=None
            )
        
        return RainfallGridResponse(
            code=200,
            message="降雨栅格数据生成成功",
            data=geojson_data
        )
        
    except ValueError as e:
        logger.error(f"时间格式错误: {e}")
        raise HTTPException(status_code=400, detail=f"时间格式错误: {str(e)}")
    except Exception as e:
        logger.error(f"生成降雨栅格失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"生成降雨栅格失败: {str(e)}")


@router.get("/stations", response_model=StationsResponse, summary="获取雨量站点数据")
async def get_rainfall_stations(
    time: str = Query(..., description="查询时间 ISO格式（自动查询前12小时或24小时数据）"),
    duration: int = Query(12, description="持续时间（小时），可选12或24", ge=12, le=24)
):
    """
    获取指定时间的雨量站点原始数据
    
    Args:
        time: 查询时间
        duration: 持续时间（12或24小时）
        
    Returns:
        站点列表，包含经纬度和降雨量
    """
    try:
        query_time = datetime.fromisoformat(time)
        
        # 调用服务层获取站点数据（自动查询前12小时或24小时数据）
        stations = rainfall_service.get_stations_data(
            query_time=query_time,
            duration=duration
        )
        
        return StationsResponse(
            code=200,
            message="查询成功",
            data=stations
        )
        
    except ValueError as e:
        logger.error(f"时间格式错误: {e}")
        raise HTTPException(status_code=400, detail=f"时间格式错误: {str(e)}")
    except Exception as e:
        logger.error(f"查询站点数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/point", summary="查询指定点位的降雨量")
async def get_rainfall_at_point(
    longitude: float,
    latitude: float,
    time: Optional[str] = None,
    duration: int = Query(12, description="持续时间（小时），可选12或24", ge=12, le=24)
):
    """
    查询指定经纬度位置的降雨量
    
    Args:
        longitude: 经度
        latitude: 纬度
        time: 查询时间（可选，默认当前时间，自动查询前12小时或24小时数据）
        duration: 持续时间（12或24小时）
        
    Returns:
        该点位的降雨量信息
    """
    try:
        from app.services.rainfall_service import RainfallService
        
        # 解析时间
        now = datetime.now()
        query_time = datetime.fromisoformat(time) if time else now
        
        # 验证duration参数
        if duration not in [12, 24]:
            raise ValueError("duration参数必须为12或24")
        
        # 调用服务层查询（自动查询前12小时或24小时数据）
        service = RainfallService()
        rainfall_info = service.get_rainfall_at_point(
            longitude=longitude,
            latitude=latitude,
            query_time=query_time,
            duration=duration
        )
        
        if not rainfall_info:
            return {
                "code": 200,
                "message": "未找到该点位的降雨数据",
                "data": None
            }
        
        return {
            "code": 200,
            "message": "查询成功",
            "data": rainfall_info
        }
        
    except Exception as e:
        logger.error(f"查询点位降雨量失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
