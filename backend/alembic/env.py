"""
Alembic 数据库迁移配置文件

作用：
1. 导入 SQLAlchemy 的 Base.metadata
2. 导入所有 ORM 模型，让 Alembic 能自动发现表结构
3. 从 app.config.settings 读取数据库连接地址
"""

from logging.config import fileConfig
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# 将 backend 目录加入 Python 搜索路径，确保可以 import app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config.settings import settings
from app.database.session import Base
from app.entity import db_models  # noqa: F401  必须导入，用于注册所有模型


config = context.config

# 使用 settings.py 中的数据库连接地址覆盖 alembic.ini 默认地址
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic 用它来对比模型和数据库表结构
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线迁移模式"""
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线迁移模式"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
