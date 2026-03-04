from typing import Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: Any = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json

                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000"]

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Database - 支持两种配置方式

    # 方式1: 直接使用 DATABASE_URL (推荐用于生产环境)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kg_agent"

    # 方式2: 分开配置 (更灵活，可选)
    # 如果设置了 POSTGRES_HOST，则使用这些配置构建 DATABASE_URL
    POSTGRES_HOST: str | None = None
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "kg_agent"

    # Pool settings for PostgreSQL
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    @property
    def effective_database_url(self) -> str:
        """获取有效的数据库 URL

        优先使用 DATABASE_URL，如果设置了 POSTGRES_HOST 则构建新 URL
        """
        if self.POSTGRES_HOST:
            return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return self.DATABASE_URL


settings = Settings()
