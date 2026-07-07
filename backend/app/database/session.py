"""
数据库连接与会话管理

职责：
- 创建 SQLAlchemy 数据库引擎
- 创建数据库会话工厂 SessionLocal
- 创建 ORM 模型基类 Base
- 提供 get_db 依赖注入函数，供 FastAPI API 层使用
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config.settings import settings


# 创建数据库引擎
# pool_pre_ping=True：每次从连接池取连接前先检查连接是否可用
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

# 数据库会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ORM 模型基类，后面的 User、DetectionTask 等模型都要继承它
Base = declarative_base()


def get_db():
    """
    获取数据库会话的 FastAPI 依赖注入函数。

    用法示例：
        from fastapi import Depends
        from sqlalchemy.orm import Session

        @router.get("/xxx")
        def my_api(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()