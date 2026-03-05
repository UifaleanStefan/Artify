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

    # Style transfer provider: "openai" (default) or "replicate"
    style_transfer_provider: str = "openai"

    # OpenAI API (when style_transfer_provider=openai)
    openai_api_key: str = ""
    openai_stylize_base_url: Optional[str] = None  # default: https://api.openai.com
    openai_stylize_model: str = "gpt-image-1.5"  # gpt-image-1.5 (better) or gpt-image-1-mini (cheaper)
    openai_stylize_quality: str = "low"  # low (~$0.01/img), medium (~$0.04), high (~$0.17)

    # Replicate API (when style_transfer_provider=replicate)
    replicate_api_token: str = ""

    # Timeouts and retries
    api_timeout_seconds: int = 120
    polling_timeout_seconds: int = 600
    polling_interval_seconds: int = 5
    max_retries: int = 3
    replicate_rate_limit_retries: int = 8
    replicate_rate_limit_base_wait_seconds: int = 40

    # File upload
    upload_dir: Optional[str] = None

    # Public base URL (for tunnels / production)
    public_base_url: Optional[str] = None

    # Database
    database_url: Optional[str] = None
    db_pool_size: int = 10
    db_max_overflow: int = 15
    result_image_ttl_days: int = 14  # Delete result image blobs from DB after this many days

    # Order processing concurrency (per process; total = this × number of Uvicorn workers)
    max_concurrent_orders: int = 8
    style_image_delay_seconds: int = 30  # Delay between style images in a pack (provider throttle)

    # Stripe payments
    stripe_secret_key: Optional[str] = None        # sk_live_... or sk_test_...
    stripe_publishable_key: Optional[str] = None   # pk_live_... or pk_test_...
    stripe_webhook_secret: Optional[str] = None    # whsec_... from Stripe dashboard

    # Email (use HTTP APIs first – SMTP often blocked on Render)
    resend_api_key: Optional[str] = None  # Free: 100/day @ resend.com
    sendgrid_api_key: Optional[str] = None  # Free: 100/day @ sendgrid.com
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    from_email: str = "noreply@artifyai.com"
    from_name: str = "Artify"

    # Private dashboard (optional): set DASHBOARD_SECRET to enable /dashboard
    dashboard_secret: Optional[str] = None

    # Rate limiting (per IP, requests per minute; 0 to disable)
    rate_limit_api_per_minute: int = 60
    rate_limit_static_per_minute: int = 120


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


def get_order_results_dir() -> Path:
    """Directory for persisting order result images (so Replicate temp URLs are not relied on)."""
    try:
        base = get_upload_dir().parent
    except Exception:
        base = Path(tempfile.gettempdir())
    p = base / "artify_order_results"
    p.mkdir(parents=True, exist_ok=True)
    return p
