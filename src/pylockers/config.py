"""Application configuration loaded from environment variables / .env file."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for the Relaxx System API client.

    Values are read from environment variables prefixed with ``RELAXX_``
    (e.g. ``RELAXX_API_KEY``) or from a local ``.env`` file.
    """

    model_config = SettingsConfigDict(
        env_prefix="RELAXX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: str = "http://localhost:5000"
    api_key: SecretStr = SecretStr("")
    timeout: float = 10.0


def get_settings() -> Settings:
    return Settings()
