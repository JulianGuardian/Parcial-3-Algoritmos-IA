from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables.

    A local `.env` file is loaded for development only. Every field has a
    non-sensitive default; invalid values make startup fail with the name of
    the offending setting.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "nubara-backend"
    environment: Literal["local", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_v1_prefix: str = "/api/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
