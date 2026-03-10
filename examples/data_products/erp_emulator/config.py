"""ERP Emulator Configuration

Configuration settings for the ERP emulator service.
"""

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Literal


class Settings(BaseSettings):
    """ERP Emulator settings"""

    # Service Configuration
    APP_NAME: str = "ERP Emulator Service"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 6688

    # Database Configuration
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/erp_emulator.db"

    # CORS Configuration
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Seed Data Configuration
    SEED_SUPPLIERS_COUNT: int = 18
    SEED_MATERIALS_COUNT: int = 24
    SEED_ORDERS_COUNT: int = 220
    SEED_CONTRACTS_COUNT: int = 35
    SEED_PAYMENTS_COUNT: int = 280

    # Pagination Defaults
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables from parent app


# Global settings instance
settings = Settings()


def get_data_dir() -> Path:
    """Get the data directory path, creating it if necessary"""
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir
