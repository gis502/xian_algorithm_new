"""
API 路由模块
"""
from fastapi import FastAPI


def register_routers(application: FastAPI):
    """注册所有路由"""
    from app.api.rainfall import router as rainfall_router
    from app.api.earthquake import router as earthquake_router

    application.include_router(rainfall_router)
    application.include_router(earthquake_router)
