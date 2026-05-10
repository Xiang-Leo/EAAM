"""
backend/app/config.py
---------------------
集中管理应用配置，通过环境变量注入，兼容 SQLite（开发）与 PostgreSQL（生产）。
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---- 数据库 --------------------------------------------------------
    DATABASE_URL: str = "sqlite:///./ancient_calculus.db"
    # 若使用 PostgreSQL，通过环境变量覆盖：
    # DATABASE_URL=postgresql+psycopg2://user:password@host:5432/eaam

    # ---- 应用基础信息 -------------------------------------------------
    APP_TITLE:       str = "EAAM API"
    APP_DESCRIPTION: str = "Ancient Chinese Dental Calculus Microbiome Database"
    APP_VERSION:     str = "1.0.0"

    # ---- CORS ---------------------------------------------------------
    CORS_ORIGINS: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",          # 忽略 .env 中与 Settings 无关的前端变量（如 NEXT_PUBLIC_*）
    )


@lru_cache
def get_settings() -> Settings:
    """返回全局单例 Settings，避免重复解析环境变量。"""
    return Settings()
