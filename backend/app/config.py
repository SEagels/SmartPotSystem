from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = "dev"
    DATABASE_URL: str = "sqlite+aiosqlite:///./storage/smartpot.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    STORAGE_BACKEND: str = "local"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "smartpot-images"

    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883

    JWT_SECRET_KEY: str = "change-me-in-production-use-random-string"
    JWT_EXPIRE_MINUTES: int = 10080

    YOLO_MODEL_PATH: str = "./models/yolov11-plant.onnx"
    LLM_API_KEY: str = ""
    LLM_API_URL: str = "https://api.openai.com/v1/chat/completions"

    @property
    def IS_DEV(self) -> bool:
        return self.ENVIRONMENT == "dev"

    @property
    def IS_PROD(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def USE_SQLITE(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


settings = Settings()
