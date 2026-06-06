"""
FastAPI 服务创建与配置
"""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.utils.api_deps import get_rainfall_model, get_earthquake_model, is_model_loaded
from app.schemas.api_schemas import HealthResponse
from app.config.paths import get_logger

logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时预加载模型"""
    logger.info("正在预加载DBN模型...")
    get_rainfall_model()
    get_earthquake_model()
    logger.info("DBN模型预加载完成")
    yield
    logger.info("应用关闭")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    application = FastAPI(
        title="西安灾害链预测服务",
        description="基于动态贝叶斯网络的暴雨/地震灾害链预测API",
        version="1.0.0",
        lifespan=lifespan,
    )

    @application.middleware("http")
    async def log_requests(request: Request, call_next):
        """请求日志中间件"""
        start = time.time()
        response = await call_next(request)
        elapsed = time.time() - start
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({elapsed:.3f}s)")
        return response

    # 注册路由
    from app.api import register_routers
    register_routers(application)

    @application.get("/health", response_model=HealthResponse, tags=["系统"])
    async def health_check():
        """健康检查"""
        status = is_model_loaded()
        return HealthResponse(status="ok", **status)

    return application
