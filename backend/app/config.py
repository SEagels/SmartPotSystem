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
    YOLO_PT_MODEL_PATH: str = "./models/best.pt"
    # ── 大模型养护建议配置 ──
    # LLM_API_KEY: 在此填写你的大模型 API Key（兼容 OpenAI 格式的 API 均可使用）
    # 若不填写，系统将使用内置规则自动生成养护建议（效果略逊于大模型）
    # 支持: OpenAI、DeepSeek、通义千问、智谱GLM 等兼容 OpenAI API 格式的服务
    # 示例: LLM_API_KEY="YOUR_LLM_API_KEY"
    LLM_API_KEY: str = ""
    # LLM_API_URL: 大模型 API 地址，默认使用 OpenAI 官方地址
    # 若使用国内模型请修改为对应地址，例如:
    #   DeepSeek: https://api.deepseek.com/v1/chat/completions
    #   通义千问: https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
    #   智谱GLM:  https://open.bigmodel.cn/api/paas/v4/chat/completions
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
