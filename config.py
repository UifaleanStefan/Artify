"""
Application configuration loaded from environment variables.
"""
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Replicate API
    replicate_api_token: str = ""

    # Timeouts and retries
    api_timeout_seconds: int = 120
    polling_timeout_seconds: int = 300
    polling_interval_seconds: int = 5
    max_retries: int = 3
    replicate_rate_limit_retries: int = 8
    replicate_rate_limit_base_wait_seconds: int = 15

    # File upload
    upload_dir: Optional[str] = None

    # Public base URL (for tunnels / production)
    public_base_url: Optional[str] = None

    # Database
    database_url: Optional[str] = None

    # Email
    sendgrid_api_key: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    from_email: str = "noreply@artifyai.com"
    from_name: str = "Artify"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_upload_dir() -> Path:
    s = get_settings()
    if s.upload_dir:
        p = Path(s.upload_dir)
    else:
        p = Path(tempfile.gettempdir()) / "artify_uploads"
    p.mkdir(parents=True, exist_ok=True)
    return p
