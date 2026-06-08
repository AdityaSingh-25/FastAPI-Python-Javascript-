from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables or .env.

    Field names map case-insensitively to env vars, so ``DATABASE_URL`` in the
    environment populates ``database_url`` here.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SaaS Product Management Dashboard API"
    app_version: str = "2.0.0"
    database_url: str = "sqlite:///./saas_products.db"
    low_stock_threshold: int = 5
    cors_origins: List[str] = ["*"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
