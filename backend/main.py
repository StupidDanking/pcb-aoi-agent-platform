"""
FastAPI 应用入口

PCB Defect Agent Platform
基于 YOLOv11 的 PCB 缺陷检测智能体平台
"""
from app.api.history import router as history_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.training import router as training_router
from app.api.detection import router as detection_router
from app.api.chat import router as chat_router
from app.api.models import router as models_router
from app.api.review import router as review_router

from app.config.settings import settings
from app.core.exceptions import register_exception_handlers
from app.core.middleware import RequestLoggingMiddleware
from app.core.logger import get_logger


logger = get_logger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "面向工业质检场景的 PCB 缺陷检测智能体平台。"
        "系统支持用户认证、PCB 图像上传、YOLOv11 缺陷检测、"
        "检测结果管理和智能分析问答。"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# 注册全局异常处理器
register_exception_handlers(app)

# 注册 API 请求日志中间件
app.add_middleware(RequestLoggingMiddleware)

# CORS 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router, prefix="/api/auth")
app.include_router(health_router)
app.include_router(training_router)
app.include_router(history_router)
app.include_router(detection_router)
app.include_router(chat_router)
app.include_router(models_router)
app.include_router(review_router)


@app.on_event("startup")
def startup_services():
    try:
        from app.storage.minio_client import init_minio

        init_minio()
        logger.info("MinIO initialized")
    except Exception as exc:
        logger.warning("MinIO init skipped: %s", exc)


@app.get("/", summary="根路径")
def root():
    """根路径接口"""
    return {
        "message": f"欢迎使用 {settings.APP_NAME}",
        "description": "基于 YOLOv11 的 PCB 缺陷检测智能体平台",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("%s 后端服务启动中...", settings.APP_NAME)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
