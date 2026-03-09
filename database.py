"""
Database setup and models for orders.
"""
import os
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, Float, Integer, LargeBinary, String, Text, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Index

from config import get_settings

Base = declarative_base()


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Order(Base):
    __tablename__ = "art_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(50), unique=True, index=True, nullable=False)
    status = Column(String(20), default=OrderStatus.PENDING.value, nullable=False)

    email = Column(String(255), nullable=False, index=True)

    style_id = Column(Integer)
    style_name = Column(String(255))

    image_url = Column(Text, nullable=False)
    portrait_mode = Column(String(20), default="realistic")  # realistic | artistic
    style_image_url = Column(Text)
    style_image_urls = Column(Text)  # JSON array of style URLs for packs (e.g. Masters 15)
    result_urls = Column(Text)  # JSON array of result image URLs

    style_transfer_job_id = Column(Text)
    style_transfer_error = Column(Text)
    replicate_prediction_details = Column(Text)  # JSON array of Replicate prediction objects: id, status, error, metrics, created_at, started_at, completed_at, result_url, model, version, source, urls, logs

    amount = Column(Float, default=9.99)
    payment_status = Column(String(20), default="pending")
    payment_provider = Column(String(50))
    payment_transaction_id = Column(String(255))

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    paid_at = Column(DateTime)
    completed_at = Column(DateTime)
    failed_at = Column(DateTime)
    retry_count = Column(Integer, default=0, nullable=False)  # number of auto-retries (max 1)

    billing_name = Column(String(255))
    billing_address = Column(Text)
    billing_city = Column(String(100))
    billing_state = Column(String(100))
    billing_zip = Column(String(20))
    billing_country = Column(String(100))


class OrderResultImage(Base):
    """Stored result image bytes for serving after redeploys. TTL applied (e.g. 14 days)."""
    __tablename__ = "art_order_result_images"

    order_id = Column(String(50), primary_key=True, nullable=False)
    image_index = Column(Integer, primary_key=True, nullable=False)  # 1-based
    content_type = Column(String(32), nullable=False, default="image/jpeg")
    data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class OrderSourceImage(Base):
    """Customer upload stored at order creation so style transfer works after redeploy."""
    __tablename__ = "art_order_source_images"

    order_id = Column(String(50), primary_key=True, nullable=False)
    content_type = Column(String(32), nullable=False, default="image/jpeg")
    data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AnalyticsEvent(Base):
    """Persistent analytics events for dashboard: page views, time on page, sessions, drop-off, referrer/UTM."""
    __tablename__ = "art_analytics_events"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    event_type = Column(String(32), default="page_view", nullable=False)
    session_id = Column(String(64), nullable=False, index=True)
    visitor_id = Column(String(64), nullable=False, index=True)
    path = Column(String(512), nullable=False, index=True)
    section = Column(String(256))
    time_on_page_sec = Column(Float)
    referrer = Column(String(1024))
    utm_source = Column(String(256))
    utm_medium = Column(String(256))
    utm_campaign = Column(String(256))
    device = Column(String(64))

    __table_args__ = (Index("ix_art_analytics_events_created_at", "created_at"),)


def get_database_url() -> str:
    settings = get_settings()
    db_url = settings.database_url or os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        db_url = os.environ.get("POSTGRES_URL", "").strip()
    if not db_url:
        # Local dev: use SQLite so the server and analytics work without PostgreSQL
        db_url = "sqlite:///./artify.db"
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return db_url


DATABASE_URL = get_database_url()
_settings = get_settings()

_engine_kw: dict = {}
if DATABASE_URL.startswith("sqlite"):
    _engine_kw["connect_args"] = {"check_same_thread": False}
    _engine_kw["pool_pre_ping"] = False  # SQLite has no pre-ping
else:
    _engine_kw["pool_pre_ping"] = True
    _engine_kw["pool_size"] = _settings.db_pool_size
    _engine_kw["max_overflow"] = _settings.db_max_overflow
    _engine_kw["connect_args"] = {"connect_timeout": 10}
engine = create_engine(DATABASE_URL, **_engine_kw)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    # Creates art_orders, art_order_result_images, art_order_source_images
    Base.metadata.create_all(bind=engine)
    # Ensure style_image_urls exists for Masters pack (existing DBs from before this column)
    for col_sql in (
        "ALTER TABLE art_orders ADD COLUMN IF NOT EXISTS portrait_mode VARCHAR(20) DEFAULT 'realistic'",
        "ALTER TABLE art_orders ADD COLUMN IF NOT EXISTS style_image_urls TEXT",
        "ALTER TABLE art_orders ADD COLUMN IF NOT EXISTS replicate_prediction_details TEXT",
        "ALTER TABLE art_orders ALTER COLUMN style_transfer_job_id TYPE TEXT",
        "ALTER TABLE art_orders ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0",
    ):
        try:
            with engine.connect() as conn:
                conn.execute(text(col_sql))
                conn.commit()
        except Exception:
            pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
