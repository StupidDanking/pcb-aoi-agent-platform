"""
FastAPI 应用入口

职责：
- 创建 FastAPI 应用实例
- 配置 CORS 跨域
- 注册 API 路由
- 提供基础健康检查接口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.auth import router as auth_router
from app.config.settings import settings
from app.database.session import engine


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="基于 YOLOv11 的目标检测智能体平台 API",
    docs_url="/docs",
    redoc_url="/redoc",
)


# CORS 跨域配置
# 允许前端 Vite 开发服务器 http://localhost:5173 访问后端
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册认证路由
# 最终接口路径：
# POST /api/auth/register
# POST /api/auth/login
# GET  /api/auth/me
app.include_router(auth_router, prefix="/api/auth")


@app.get("/", summary="根路径")
def root():
    """根路径接口"""
    return {
        "message": f"欢迎使用 {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/api/health", summary="健康检查")
def health_check():
    """
    健康检查接口。

    当前先检查后端服务和数据库连接。
    Redis、MinIO 的深入检查后面 Day4 可继续完善。
    """
    database_status = "unknown"

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception as e:
        database_status = f"error: {str(e)}"

    return {
        "code": 200,
        "message": "ok",
        "data": {
            "status": "healthy" if database_status == "ok" else "degraded",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "database": database_status,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
