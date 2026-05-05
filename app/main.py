"""
FastAPI应用主文件
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.core.database import db_manager
from app.utils.logger import setup_logging
from app.api.rainfall import router as rainfall_router

# 初始化日志
logger = setup_logging()

# 获取配置
settings = get_settings()


def create_application() -> FastAPI:
    """创建FastAPI应用实例"""
    
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        description="基于FastAPI的现代化Web应用框架"
    )
    
    # 配置CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS if hasattr(settings, 'CORS_ORIGINS') else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return application


# 创建应用实例
app = create_application()


# ==================== 启动和关闭事件 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    logger.info(f"正在启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"环境: {settings.ENVIRONMENT}")
    logger.info(f"数据库连接: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    
    # 测试数据库连接
    if db_manager.test_connection():
        logger.info("数据库连接成功")
    else:
        logger.warning("数据库连接失败，请检查配置")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    logger.info("应用正在关闭...")


# ==================== 根路径和健康检查 ====================

@app.get("/", tags=["基础"])
async def root():
    """根路径 - 欢迎信息"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT.value,
        "status": "running"
    }


@app.get("/health", tags=["基础"])
async def health_check():
    """健康检查接口"""
    try:
        # 检查数据库连接
        db_manager.execute_raw_sql("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "app_version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT.value
    }


# ==================== 注册路由 ====================

app.include_router(rainfall_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.RELOAD if hasattr(settings, 'RELOAD') else settings.DEBUG
    )
