from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 应用基础配置
    APP_NAME: str = "PCB AOI Agent Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 5

    # PostgreSQL 数据库配置
    # 暂时保留 rsod_agent，避免重建 Docker volume 和 Alembic 迁移。
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "pcb_aoi_agent"
    DB_USER: str = "pcb_aoi_admin"
    DB_PASSWORD: str = "pcb_aoi_password"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # MinIO 配置
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "pcb-aoi-images"
    MINIO_SECURE: bool = False
    
     # YOLOv11 训练配置
    TRAIN_OUTPUT_DIR: str = "runs/train"
    DATASET_BASE_DIR: str = "../datasets/pcb_defect"
    DEFAULT_YOLO_MODEL: str = "yolo11n.pt"
    DEFAULT_TRAIN_DEVICE: str = "0"
    
    # JWT 配置
    JWT_SECRET_KEY: str = "pcb-aoi-dev-secret-key-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS 配置
    ALLOWED_ORIGINS: str = (
        "http://localhost:3000,"
        "http://localhost:5173,"
        "http://localhost:8080"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )


settings = Settings()
