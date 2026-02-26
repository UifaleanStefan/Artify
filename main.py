"""
FastAPI application for AI art style transfer.
"""
import asyncio
import io
import json
import logging
import re
import shutil
import sys
import time
import uuid
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncGenerator, Optional
from urllib.parse import urlparse

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from clients import (
    OpenAIStylizeClient,
    ReplicateClient,
    StyleTransferError,
    StyleTransferRateLimit,
    StyleTransferTimeout,
)
from config import get_settings, get_upload_dir, get_order_results_dir


def _resolve_style_image_url(style_image_url: Optional[str]) -> Optional[str]:
    """If style_image_url is relative, make it absolute using PUBLIC_BASE_URL (required for API)."""
    if not style_image_url or not style_image_url.strip():
        return style_image_url
    url = style_image_url.strip()
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("/"):
        base = (get_settings().public_base_url or "").rstrip("/")
        return f"{base}{url}" if base else url
    return url


def _persist_result_images(order_id: str, result_items: list) -> list[str]:
    """
    Persist result images to DB and disk. Each item can be:
    - str (URL): fetch and persist
    - dict with "content" (bytes) and "content_type": decode and persist directly (OpenAI b64)
    Returns list of permanent URLs.
    """
    base_url = (get_settings().public_base_url or "").rstrip("/")
    if not base_url:
        logger.warning("PUBLIC_BASE_URL not set; cannot create permanent result URLs")
        return [str(x) if isinstance(x, str) else "" for x in result_items]
    try:
        results_dir = get_order_results_dir() / order_id
        results_dir.mkdir(parents=True, exist_ok=True)
        permanent = []
        db = SessionLocal()
        try:
            for i, item in enumerate(result_items, start=1):
                try:
                    if isinstance(item, dict) and "content" in item:
                        content = item["content"]
                        content_type = item.get("content_type", "image/jpeg").split(";")[0].strip()
                    else:
                        url = str(item)
                        if not url.startswith(("http://", "https://")):
                            logger.debug(
                                "Skipping persist for result image %s (non-fetchable placeholder): %s",
                                i, url[:50] if len(url) > 50 else url,
                            )
                            permanent.append("")
                            continue
                        with httpx.Client(timeout=45) as client:
                            r = client.get(url)
                        if r.status_code >= 400:
                            logger.warning("Failed to fetch result image %s for %s: %s", i, order_id, r.status_code)
                            permanent.append(url)
                            continue
                        content = r.content
                        content_type = r.headers.get("content-type", "image/jpeg").split(";")[0].strip()
                    if content_type not in ("image/jpeg", "image/png", "image/webp"):
                        content_type = "image/jpeg"
                    # Store in DB (survives redeploy)
                    row = OrderResultImage(
                        order_id=order_id,
                        image_index=i,
                        content_type=content_type,
                        data=content,
                    )
                    db.merge(row)
                    # Also write to disk for backward compat and redundancy
                    ext = "jpg"
                    if "png" in content_type:
                        ext = "png"
                    elif "webp" in content_type:
                        ext = "webp"
                    path = results_dir / f"{i}.{ext}"
                    path.write_bytes(content)
                    permanent.append(f"{base_url}/api/orders/{order_id}/result/{i}")
                except Exception as e:
                    logger.warning("Persist result image %s for %s failed: %s", i, order_id, e)
                    permanent.append(str(item) if isinstance(item, str) else "")
            if len(permanent) == len(result_items):
                db.commit()
                logger.info("Persisted %d result images for order %s (DB + disk)", len(permanent), order_id)
                return permanent
            db.rollback()
        finally:
            db.close()
    except Exception as e:
        logger.warning("Persist result images for %s failed: %s", order_id, e)
    return [str(x) if isinstance(x, str) else "" for x in result_items]


from database import Order, OrderResultImage, OrderSourceImage, OrderStatus, get_db, SessionLocal, init_db
from models import StyleTransferResponse
from models.order_schemas import OrderCreateRequest, OrderResponse, OrderStatusResponse
from services import StyleTransferService
from services.email_service import EmailService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)
# Reduce noisy per-request polling logs from httpx/httpcore.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

STATIC_DIR = Path(__file__).parent / "static"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
_ACTIVE_ORDER_TASKS: set[str] = set()
_DB_INIT_STARTED = False

# Orders older than this are deleted by the TTL cleanup job
ORDER_TTL_DAYS = 14


def get_provider() -> ReplicateClient | OpenAIStylizeClient:
    settings = get_settings()
    provider = (settings.style_transfer_provider or "openai").strip().lower()
    if provider == "replicate":
        return ReplicateClient(
            api_token=settings.replicate_api_token,
            timeout_seconds=settings.api_timeout_seconds,
            polling_timeout_seconds=settings.polling_timeout_seconds,
            polling_interval_seconds=settings.polling_interval_seconds,
            rate_limit_retries=settings.replicate_rate_limit_retries,
            rate_limit_base_wait=float(settings.replicate_rate_limit_base_wait_seconds),
        )
    return OpenAIStylizeClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_stylize_base_url,
        timeout_seconds=settings.api_timeout_seconds,
        model=settings.openai_stylize_model or "gpt-image-1.5",
        quality=settings.openai_stylize_quality or "low",
        rate_limit_retries=settings.replicate_rate_limit_retries,
        rate_limit_base_wait=float(settings.replicate_rate_limit_base_wait_seconds),
    )


def get_service() -> StyleTransferService:
    return StyleTransferService(provider=get_provider())


def get_replicate_service() -> Optional[StyleTransferService]:
    """Replicate service for fallback when OpenAI fails. Returns None if replicate_api_token is not set."""
    settings = get_settings()
    if not (settings.replicate_api_token or "").strip():
        return None
    return StyleTransferService(
        provider=ReplicateClient(
            api_token=settings.replicate_api_token,
            timeout_seconds=settings.api_timeout_seconds,
            polling_timeout_seconds=settings.polling_timeout_seconds,
            polling_interval_seconds=settings.polling_interval_seconds,
            rate_limit_retries=settings.replicate_rate_limit_retries,
            rate_limit_base_wait=float(settings.replicate_rate_limit_base_wait_seconds),
        )
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Artify service starting")
    s = get_settings()
    provider = (s.style_transfer_provider or "openai").strip().lower()
    logger.info("Style transfer provider: %s", provider)
    if provider == "openai" and not s.openai_api_key:
        logger.warning("OPENAI_API_KEY not set; style transfer will fail at runtime")
    if s.resend_api_key:
        logger.info("Email: Resend (RESEND_API_KEY set)")
    elif s.sendgrid_api_key:
        logger.info("Email: SendGrid (SENDGRID_API_KEY set)")
    elif s.smtp_host:
        logger.info("Email: SMTP (%s:%s)", s.smtp_host, s.smtp_port)
    else:
        logger.warning("Email: No provider configured (set RESEND_API_KEY in Render env)")
    get_upload_dir().mkdir(parents=True, exist_ok=True)
    _start_db_init_once()
    supervisor_task = asyncio.create_task(_processing_supervisor_loop())
    cleanup_task = asyncio.create_task(_ttl_cleanup_loop())
    yield
    supervisor_task.cancel()
    cleanup_task.cancel()
    try:
        await supervisor_task
    except asyncio.CancelledError:
        pass
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("Artify service shutting down")


def _start_db_init_once() -> None:
    """Start automatic DB init/migration in background exactly once per process."""
    global _DB_INIT_STARTED
    if _DB_INIT_STARTED:
        return
    _DB_INIT_STARTED = True
    asyncio.get_event_loop().run_in_executor(None, _run_db_init_background)


def _run_db_init_background() -> None:
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.exception("Automatic DB init failed: %s", e)


app = FastAPI(
    title="Artify – AI Art Style Transfer",
    description="Transform photos into famous art styles",
    version="1.0.0",
    lifespan=lifespan,
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return JSON 500 for unhandled exceptions; never leak stack to client."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "A server error occurred. Please try again later."},
    )


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Prevent HTML from being cached so users always get latest after deploy
_HTML_HEADERS = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}


# ── Page routes ──────────────────────────────────────────────

@app.get("/health")
async def health() -> JSONResponse:
    """Lightweight health endpoint for uptime checks."""
    return JSONResponse({"status": "ok"})

@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "landing" / "index.html", headers=_HTML_HEADERS)

@app.get("/styles")
async def styles_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "landing" / "styles.html", headers=_HTML_HEADERS)

@app.get("/upload")
async def upload_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "landing" / "upload.html", headers=_HTML_HEADERS)

@app.get("/details")
async def details_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "landing" / "details.html", headers=_HTML_HEADERS)

@app.get("/billing")
async def billing_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "landing" / "billing.html", headers=_HTML_HEADERS)

@app.get("/payment")
async def payment_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "landing" / "payment.html", headers=_HTML_HEADERS)

@app.get("/create/done")
async def done_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "landing" / "create_done.html", headers=_HTML_HEADERS)


@app.get("/help")
async def help_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "landing" / "help.html", headers=_HTML_HEADERS)


@app.get("/contact")
async def contact_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "landing" / "contact.html", headers=_HTML_HEADERS)


@app.get("/terms")
async def terms_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "landing" / "terms.html", headers=_HTML_HEADERS)


@app.get("/privacy")
async def privacy_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "landing" / "privacy.html", headers=_HTML_HEADERS)


@app.get("/marketing")
async def marketing_page() -> FileResponse:
    """Marketing page: single high-quality style transfer demo."""
    return FileResponse(STATIC_DIR / "landing" / "marketing.html", headers=_HTML_HEADERS)


@app.get("/order/{order_id}")
async def order_status_page(order_id: str) -> FileResponse:
    """Page where users can view order status and result images (e.g. /order/ART-xxx)."""
    return FileResponse(STATIC_DIR / "landing" / "order_status.html", headers=_HTML_HEADERS)


@app.get("/debug/order")
async def debug_order_page() -> FileResponse:
    """Debug page: enter order ID or URL to view all results and prediction details."""
    return FileResponse(STATIC_DIR / "landing" / "debug_order.html", headers=_HTML_HEADERS)


@app.get("/debug/last-results")
async def debug_last_results_page() -> FileResponse:
    """Debug page: show all result images from the last order that has results."""
    return FileResponse(STATIC_DIR / "landing" / "debug_last_results.html", headers=_HTML_HEADERS)


@app.get("/api/debug/last-order", response_model=OrderStatusResponse)
async def get_last_order_status(db: Session = Depends(get_db)) -> OrderStatusResponse:
    """Return status and results of the most recent order (by id). For debugging."""
    order = db.query(Order).order_by(Order.id.desc()).first()
    if not order:
        raise HTTPException(status_code=404, detail="No orders found")
    return OrderStatusResponse(
        order_id=order.order_id,
        status=order.status,
        result_urls=order.result_urls,
        replicate_prediction_details=order.replicate_prediction_details,
        error=order.style_transfer_error,
    )


@app.get("/api/debug/last-order-results")
async def get_last_order_results(db: Session = Depends(get_db)) -> JSONResponse:
    """Return the 15 (or N) result image URLs from the most recent order that has results. For debugging."""
    order, urls = _last_order_with_result_urls(db)
    if not order:
        raise HTTPException(status_code=404, detail="No order with result images found")
    return JSONResponse(
        content={
            "order_id": order.order_id,
            "status": order.status,
            "count": len(urls),
            "result_urls": urls,
        }
    )


@app.post("/api/debug/resume-order/{order_id}")
async def resume_order(order_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Resume a stuck processing order (e.g. after host killed the worker). Picks up from last saved result."""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.PROCESSING.value:
        raise HTTPException(status_code=400, detail=f"Order not processing (status={order.status})")
    background_tasks.add_task(process_order_style_transfer, order_id)
    return {"status": "ok", "message": "Resume task queued", "order_id": order_id}


@app.get("/api/debug/last-order-results.txt")
async def get_last_order_results_txt(db: Session = Depends(get_db)):
    """Return only the image URLs from the last order with results, one per line (what the API sent back)."""
    order, urls = _last_order_with_result_urls(db)
    if not order or not urls:
        raise HTTPException(status_code=404, detail="No order with result images found")
    return PlainTextResponse("\n".join(urls))


@app.post("/api/debug/resend-ready-email/{order_id}")
async def resend_ready_email(order_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Resend ready email for a completed order with result images."""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail=f"Order is not completed (status={order.status})")
    if not order.result_urls:
        raise HTTPException(status_code=400, detail="Order has no result images")
    try:
        urls = json.loads(order.result_urls) if isinstance(order.result_urls, str) else (order.result_urls or [])
    except Exception:
        urls = []
    if not isinstance(urls, list) or not urls:
        raise HTTPException(status_code=400, detail="Order has no valid result images")

    styles = _load_styles_data()
    result_labels = _build_result_labels(order, urls, styles)
    background_tasks.add_task(
        EmailService().send_result_ready,
        order.order_id,
        order.email,
        urls,
        order.style_name,
        result_labels,
    )
    return {"status": "ok", "message": "Ready email resend queued", "order_id": order_id, "email": order.email}


def _last_order_with_result_urls(db: Session):
    """Return (order, list of result URLs) for the most recent order that has result_urls."""
    order = (
        db.query(Order)
        .filter(Order.result_urls.isnot(None), Order.result_urls != "")
        .order_by(Order.id.desc())
        .first()
    )
    urls = []
    if order and order.result_urls:
        try:
            urls = json.loads(order.result_urls) if isinstance(order.result_urls, str) else (order.result_urls or [])
        except Exception:
            pass
    return order, urls


def _target_image_count(order: Order) -> int:
    """How many style outputs this order should produce."""
    if order.style_image_urls:
        try:
            arr = json.loads(order.style_image_urls) if isinstance(order.style_image_urls, str) else (order.style_image_urls or [])
            if isinstance(arr, list):
                return len(arr)
        except Exception:
            pass
    return 1 if order.style_image_url else 0


def _done_image_count(order: Order) -> int:
    if not order.result_urls:
        return 0
    try:
        arr = json.loads(order.result_urls) if isinstance(order.result_urls, str) else (order.result_urls or [])
        return len(arr) if isinstance(arr, list) else 0
    except Exception:
        return 0


async def _processing_supervisor_loop() -> None:
    """Self-heal stuck orders without external cron.
    Scans paid/processing orders and re-queues unfinished ones.
    """
    # Let app finish startup before first DB scan.
    await asyncio.sleep(2)
    while True:
        _start_db_init_once()
        try:
            order_ids = await asyncio.to_thread(_get_unfinished_order_ids_sync)
            for order_id in order_ids:
                if order_id in _ACTIVE_ORDER_TASKS:
                    continue
                asyncio.create_task(process_order_style_transfer(order_id))
        except Exception as e:
            logger.warning("Supervisor loop temporary DB/error: %s", e)
        await asyncio.sleep(20)


def _get_unfinished_order_ids_sync() -> list[str]:
    """Blocking DB scan run in thread; returns orders needing work."""
    db = SessionLocal()
    try:
        orders = db.query(Order).filter(
            Order.status.in_([OrderStatus.PAID.value, OrderStatus.PROCESSING.value])
        ).all()
        order_ids = []
        for o in orders:
            target = _target_image_count(o)
            done = _done_image_count(o)
            if target > 0 and done < target:
                order_ids.append(o.order_id)
        return order_ids
    finally:
        db.close()


def _cleanup_expired_orders_sync() -> int:
    """Delete orders older than ORDER_TTL_DAYS and their persisted result images. Returns count deleted."""
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=ORDER_TTL_DAYS)
        expired = db.query(Order).filter(Order.created_at < cutoff).all()
        deleted = 0
        results_dir = get_order_results_dir()
        for order in expired:
            try:
                order_dir = results_dir / order.order_id
                if order_dir.exists() and order_dir.is_dir():
                    shutil.rmtree(order_dir, ignore_errors=True)
            except Exception as e:
                logger.warning("TTL cleanup: failed to remove result dir for %s: %s", order.order_id, e)
            db.query(OrderResultImage).filter(OrderResultImage.order_id == order.order_id).delete()
            db.delete(order)
            deleted += 1
        if deleted:
            db.commit()
            logger.info("TTL cleanup: deleted %d order(s) older than %d days", deleted, ORDER_TTL_DAYS)
        return deleted
    except Exception as e:
        logger.warning("TTL cleanup failed: %s", e)
        db.rollback()
        return 0
    finally:
        db.close()


def _cleanup_expired_result_images_sync() -> int:
    """Delete OrderResultImage rows older than result_image_ttl_days. Returns count deleted."""
    db = SessionLocal()
    try:
        ttl_days = get_settings().result_image_ttl_days
        cutoff = datetime.utcnow() - timedelta(days=ttl_days)
        deleted = db.query(OrderResultImage).filter(OrderResultImage.created_at < cutoff).delete()
        if deleted:
            db.commit()
            logger.info("TTL cleanup: deleted %d result image blob(s) older than %d days", deleted, ttl_days)
        return deleted
    except Exception as e:
        logger.warning("Result images TTL cleanup failed: %s", e)
        db.rollback()
        return 0
    finally:
        db.close()


def _run_ttl_cleanup_sync() -> None:
    """Run both order and result-image TTL cleanups."""
    _cleanup_expired_orders_sync()
    _cleanup_expired_result_images_sync()


async def _ttl_cleanup_loop() -> None:
    """Run TTL cleanup at startup (after delay) and then every 24 hours."""
    await asyncio.sleep(120)
    while True:
        try:
            await asyncio.to_thread(_run_ttl_cleanup_sync)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning("TTL cleanup loop error: %s", e)
        await asyncio.sleep(24 * 3600)


# ── Upload API ───────────────────────────────────────────────

def _upload_to_litterbox(file_path: str, filename: str) -> str:
    """Upload file to Litterbox (catbox) temporary hosting. Returns public URL."""
    with open(file_path, "rb") as f:
        r = httpx.post(
            "https://litterbox.catbox.moe/resources/internals/api.php",
            data={"reqtype": "fileupload", "time": "72h"},
            files={"fileToUpload": (filename, f)},
            timeout=60,
        )
    if r.status_code == 200 and r.text.strip().startswith("http"):
        return r.text.strip()
    raise HTTPException(status_code=502, detail="Failed to upload to temporary hosting")


def _build_public_upload_url(upload_id: str, ext: str) -> str:
    base = (get_settings().public_base_url or "").rstrip("/")
    if not base:
        return ""
    return f"{base}/api/uploads/{upload_id}/photo{ext}"


def _is_our_upload_url(url: str) -> bool:
    """True if url is our /api/uploads/... (lost on redeploy unless persisted)."""
    base = (get_settings().public_base_url or "").rstrip("/")
    if not base or not url or not url.strip().startswith("https://"):
        return False
    prefix = base.rstrip("/") + "/api/uploads/"
    return url.strip().startswith(prefix)


def _parse_upload_id_and_filename(url: str):
    """If url is our upload URL, return (upload_id, filename); else None."""
    base = (get_settings().public_base_url or "").rstrip("/")
    if not base or not url or not url.strip().startswith("https://"):
        return None
    prefix = base.rstrip("/") + "/api/uploads/"
    u = url.strip()
    if not u.startswith(prefix):
        return None
    rest = u[len(prefix):]
    parts = rest.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    upload_id, filename = parts[0], parts[1].split("?")[0]
    if Path(filename).suffix.lower() not in IMAGE_EXTENSIONS:
        return None
    return (upload_id, filename)


@app.get("/api/uploads/{upload_id}/{filename}")
async def get_uploaded_image(upload_id: str, filename: str):
    """Serve uploaded source images via this backend domain."""
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    ext = Path(filename).suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported format")
    file_path = get_upload_dir() / upload_id / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@app.post("/api/upload-image")
async def upload_image(file: UploadFile = File(...)) -> JSONResponse:
    """Upload a face photo. Returns public image_url."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}")

    upload_id = uuid.uuid4().hex[:12]
    upload_dir = get_upload_dir() / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"photo{ext}"

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File must be under 10 MB")

    file_path.write_bytes(content)
    logger.info(f"Image saved: {file_path} ({len(content)} bytes)")

    settings = get_settings()
    if settings.public_base_url:
        # Prefer self-hosted HTTPS URL for reliability; avoids litterbox outages/expiry.
        image_url = _build_public_upload_url(upload_id, ext)
    else:
        image_url = _upload_to_litterbox(str(file_path), f"photo{ext}")

    return JSONResponse({"image_url": image_url})


# ── Styles data helper ───────────────────────────────────────

# Masters pack: one style, 15 reference images (user gets photo in all 15)
STYLE_ID_MASTERS_PACK = 13
MASTERS_PACK_PATHS = [
    # Best 5 first (used for 5-pack tier)
    "/static/landing/styles/masters/masters-02.jpg",  # Mona Lisa
    "/static/landing/styles/masters/masters-04.jpg",  # The Scream
    "/static/landing/styles/masters/masters-15.jpg",  # Persistence of Memory
    "/static/landing/styles/masters/masters-01.jpg",  # Creation of Adam
    "/static/landing/styles/masters/masters-13.jpg",  # Sunflowers
    # Remaining 10
    "/static/landing/styles/masters/masters-03.jpg",
    "/static/landing/styles/masters/masters-05.jpg",
    "/static/landing/styles/masters/masters-06.jpg",
    "/static/landing/styles/masters/masters-07.jpg",
    "/static/landing/styles/masters/masters-08.jpg",
    "/static/landing/styles/masters/masters-09.jpg",
    "/static/landing/styles/masters/masters-10.jpg",
    "/static/landing/styles/masters/masters-11.jpg",
    "/static/landing/styles/masters/masters-12.jpg",
    "/static/landing/styles/masters/masters-14.jpg",
]

# Impression & Color pack: 15 reference images
STYLE_ID_IMPRESSION_COLOR_PACK = 14
IMPRESSION_COLOR_PACK_PATHS = [
    # Best 5 first (used for 5-pack tier)
    "/static/landing/styles/impression-color/impression-color-13.jpg",  # Starry Night
    "/static/landing/styles/impression-color/impression-color-02.jpg",  # Water Lilies
    "/static/landing/styles/impression-color/impression-color-01.jpg",  # Night city (Van Gogh)
    "/static/landing/styles/impression-color/impression-color-08.jpg",  # Irises
    "/static/landing/styles/impression-color/impression-color-11.jpg",  # Bal du Moulin de la Galette
    # Remaining 10
    "/static/landing/styles/impression-color/impression-color-03.jpg",
    "/static/landing/styles/impression-color/impression-color-04.jpg",
    "/static/landing/styles/impression-color/impression-color-05.jpg",
    "/static/landing/styles/impression-color/impression-color-06.jpg",
    "/static/landing/styles/impression-color/impression-color-07.jpg",
    "/static/landing/styles/impression-color/impression-color-09.jpg",
    "/static/landing/styles/impression-color/impression-color-10.jpg",
    "/static/landing/styles/impression-color/impression-color-12.jpg",
    "/static/landing/styles/impression-color/impression-color-14.jpg",
    "/static/landing/styles/impression-color/impression-color-15.jpg",
]

# Modern & Abstract pack: 15 reference images (modern-abstract-01.jpg … 13.png … 15.jpg)
STYLE_ID_MODERN_ABSTRACT_PACK = 15
MODERN_ABSTRACT_PACK_PATHS = [
    # Best 5 first (used for 5-pack tier)
    "/static/landing/styles/modern-abstract/modern-abstract-09.jpg",   # The Scream (Munch)
    "/static/landing/styles/modern-abstract/modern-abstract-12.jpg",   # Persistence of Memory (Dalí)
    "/static/landing/styles/modern-abstract/modern-abstract-03.jpg",   # Pollock drip
    "/static/landing/styles/modern-abstract/modern-abstract-02.jpg",   # Rothko color fields
    "/static/landing/styles/modern-abstract/modern-abstract-15.jpg",   # Les Demoiselles (Picasso)
    # Remaining 10
    "/static/landing/styles/modern-abstract/modern-abstract-01.jpg",
    "/static/landing/styles/modern-abstract/modern-abstract-04.jpg",
    "/static/landing/styles/modern-abstract/modern-abstract-05.jpg",
    "/static/landing/styles/modern-abstract/modern-abstract-06.jpg",
    "/static/landing/styles/modern-abstract/modern-abstract-07.jpg",
    "/static/landing/styles/modern-abstract/modern-abstract-08.jpg",
    "/static/landing/styles/modern-abstract/modern-abstract-10.jpg",
    "/static/landing/styles/modern-abstract/modern-abstract-11.jpg",
    "/static/landing/styles/modern-abstract/modern-abstract-13.png",
    "/static/landing/styles/modern-abstract/modern-abstract-14.jpg",
]

# Ancient Worlds pack: 15 reference images (oldest in Downloads = 01, newest = 15)
STYLE_ID_ANCIENT_WORLDS_PACK = 16
ANCIENT_WORLDS_PACK_PATHS = [
    # Best 5 first (used for 5-pack tier)
    "/static/landing/styles/ancient-worlds/ancient-worlds-11.jpg",  # Fayum Mummy Portraits
    "/static/landing/styles/ancient-worlds/ancient-worlds-01.jpg",  # Egyptian tomb painting
    "/static/landing/styles/ancient-worlds/ancient-worlds-08.jpg",  # Alexander Mosaic (Rome)
    "/static/landing/styles/ancient-worlds/ancient-worlds-05.jpg",  # Greek black-figure amphora
    "/static/landing/styles/ancient-worlds/ancient-worlds-13.jpg",  # Ishtar Gate (Babylon)
    # Remaining 10
    "/static/landing/styles/ancient-worlds/ancient-worlds-02.jpg",
    "/static/landing/styles/ancient-worlds/ancient-worlds-03.jpg",
    "/static/landing/styles/ancient-worlds/ancient-worlds-04.jpg",
    "/static/landing/styles/ancient-worlds/ancient-worlds-06.jpg",
    "/static/landing/styles/ancient-worlds/ancient-worlds-07.jpg",
    "/static/landing/styles/ancient-worlds/ancient-worlds-09.jpg",
    "/static/landing/styles/ancient-worlds/ancient-worlds-10.jpg",
    "/static/landing/styles/ancient-worlds/ancient-worlds-12.jpg",
    "/static/landing/styles/ancient-worlds/ancient-worlds-14.jpg",
    "/static/landing/styles/ancient-worlds/ancient-worlds-15.jpg",
]

# Evolution of Portraits pack: 15 reference images (oldest in Downloads = 01, newest = 15)
STYLE_ID_EVOLUTION_PORTRAITS_PACK = 17
EVOLUTION_PORTRAITS_PACK_PATHS = [
    # Best 5 first (used for 5-pack tier)
    "/static/landing/styles/evolution-portraits/evolution-portraits-08.jpg",  # Girl with a Pearl Earring
    "/static/landing/styles/evolution-portraits/evolution-portraits-05.jpg",  # Mona Lisa (Leonardo)
    "/static/landing/styles/evolution-portraits/evolution-portraits-15.jpg",  # Marilyn Diptych (Warhol)
    "/static/landing/styles/evolution-portraits/evolution-portraits-14.jpg",  # Frida Kahlo
    "/static/landing/styles/evolution-portraits/evolution-portraits-11.jpg",  # Van Gogh self-portrait
    # Remaining 10
    "/static/landing/styles/evolution-portraits/evolution-portraits-01.jpg",
    "/static/landing/styles/evolution-portraits/evolution-portraits-02.jpg",
    "/static/landing/styles/evolution-portraits/evolution-portraits-03.jpg",
    "/static/landing/styles/evolution-portraits/evolution-portraits-04.png",
    "/static/landing/styles/evolution-portraits/evolution-portraits-06.jpg",
    "/static/landing/styles/evolution-portraits/evolution-portraits-07.jpg",
    "/static/landing/styles/evolution-portraits/evolution-portraits-09.jpg",
    "/static/landing/styles/evolution-portraits/evolution-portraits-10.jpg",
    "/static/landing/styles/evolution-portraits/evolution-portraits-12.jpg",
    "/static/landing/styles/evolution-portraits/evolution-portraits-13.jpg",
]

# Royalty & Power Portraits pack: 15 reference images (oldest in Downloads = 01, newest = 15)
STYLE_ID_ROYALTY_PORTRAITS_PACK = 18
ROYALTY_PORTRAITS_PACK_PATHS = [
    # Best 5 first (used for 5-pack tier)
    "/static/landing/styles/royalty-portraits/royalty-portraits-01.jpg",  # Napoleon Crossing the Alps
    "/static/landing/styles/royalty-portraits/royalty-portraits-03.jpg",  # Henry VIII (Holbein)
    "/static/landing/styles/royalty-portraits/royalty-portraits-12.jpg",  # Arcimboldo Vertumnus
    "/static/landing/styles/royalty-portraits/royalty-portraits-02.jpg",  # Louis XIV (Rigaud)
    "/static/landing/styles/royalty-portraits/royalty-portraits-09.jpg",  # The Blue Boy (Gainsborough)
    # Remaining 10
    "/static/landing/styles/royalty-portraits/royalty-portraits-04.jpg",
    "/static/landing/styles/royalty-portraits/royalty-portraits-05.jpg",
    "/static/landing/styles/royalty-portraits/royalty-portraits-06.jpg",
    "/static/landing/styles/royalty-portraits/royalty-portraits-07.jpg",
    "/static/landing/styles/royalty-portraits/royalty-portraits-08.jpg",
    "/static/landing/styles/royalty-portraits/royalty-portraits-10.jpg",
    "/static/landing/styles/royalty-portraits/royalty-portraits-11.jpg",
    "/static/landing/styles/royalty-portraits/royalty-portraits-13.jpg",
    "/static/landing/styles/royalty-portraits/royalty-portraits-14.jpg",
    "/static/landing/styles/royalty-portraits/royalty-portraits-15.jpg",
]

# Per-image (painting title, artist) for email captions.
# Masters pack: 15 reference images (masters-01.jpg … masters-15.jpg); each result image gets the label at the same index.
# Verified 2025-02: labels match actual images in pack.
MASTERS_PACK_LABELS: list[tuple[str, str]] = [
    # Best 5 first (used for 5-pack tier)
    ("Mona Lisa", "Leonardo da Vinci"),                      # 02
    ("Strigătul", "Edvard Munch"),                           # 04
    ("Persistența memoriei", "Salvador Dalí"),               # 15
    ("Crearea lui Adam", "Michelangelo"),                    # 01
    ("Flori de floarea-soarelui", "Vincent van Gogh"),        # 13
    # Remaining 10
    ("Compoziție cu grile", "Piet Mondrian"),                # 03
    ("3 Mai 1808", "Francisco Goya"),                        # 05
    ("Judith și Holoferne", "Caravaggio"),                   # 06
    ("Străjirea de noapte", "Rembrandt van Rijn"),            # 07
    ("Las Meninas", "Diego Velázquez"),                      # 08
    ("Stilul clarobscur", "Rembrandt van Rijn"),              # 09
    ("Compoziția VIII", "Wassily Kandinsky"),                 # 10
    ("Impresie, răsărit de soare", "Claude Monet"),          # 11
    ("Pranzul la barcă", "Pierre-Auguste Renoir"),            # 12
    ("Domnișoarele din Avignon", "Pablo Picasso"),            # 14
]
# Impression & Color pack: verified 2025-02 - labels match actual images.
IMPRESSION_COLOR_PACK_LABELS: list[tuple[str, str]] = [
    # Best 5 first (used for 5-pack tier)
    ("Noapte înstelată", "Vincent van Gogh"),                # 13 - Starry Night
    ("Nufări", "Claude Monet"),                              # 02
    ("Noapte înstelată (stradă)", "Vincent van Gogh"),       # 01 - night city street
    ("Irisi", "Vincent van Gogh"),                           # 08
    ("Balul de la Moulin de la Galette", "Pierre-Auguste Renoir"),  # 11
    # Remaining 10
    ("Clasa de balet", "Edgar Degas"),                       # 03
    ("D'où venons-nous...", "Paul Gauguin"),                 # 04
    ("Femeie cu perdeau", "Claude Monet"),                   # 05
    ("Podul japonez", "Claude Monet"),                       # 06
    ("Impresie, răsărit de soare", "Claude Monet"),          # 07
    ("Muntele Sainte-Victoire", "Paul Cézanne"),             # 09
    ("Pranzul la barcă", "Pierre-Auguste Renoir"),           # 10
    ("Leagănul", "Pierre-Auguste Renoir"),                   # 12
    ("Terasa cafenelei noaptea", "Vincent van Gogh"),        # 14
    ("Flori de floarea-soarelui", "Vincent van Gogh"),       # 15
]
# Modern & Abstract pack: (titlu operă, artist) per imagine, verificate vizual
# 01–15 = modern-abstract-01.jpg … 13.png … 15.jpg
MODERN_ABSTRACT_PACK_LABELS: list[tuple[str, str]] = [
    # Best 5 first (used for 5-pack tier)
    ("The Scream", "Edvard Munch"),                       # 09
    ("The Persistence of Memory", "Salvador Dalí"),       # 12
    ("Convergence", "Jackson Pollock"),                   # 03
    ("Orange and Yellow", "Mark Rothko"),                 # 02
    ("Les Demoiselles d'Avignon", "Pablo Picasso"),       # 15
    # Remaining 10
    ("Composition VIII", "Wassily Kandinsky"),            # 01
    ("Black Square", "Kazimir Malevich"),                 # 04
    ("Broadway Boogie Woogie", "Piet Mondrian"),          # 05
    ("Woman I", "Willem de Kooning"),                     # 06
    ("Street, Dresden", "Ernst Ludwig Kirchner"),         # 07
    ("Blue Horse I", "Franz Marc"),                       # 08
    ("The Lovers", "René Magritte"),                      # 10
    ("The Elephants", "Salvador Dalí"),                   # 11
    ("Man with a Guitar", "Georges Braque"),              # 13
    ("Girl with a Mandolin", "Pablo Picasso"),            # 14
]
# Ancient Worlds pack: 01 = first downloaded … 15 = last downloaded (see setup_ancient_worlds_pack.py)
ANCIENT_WORLDS_PACK_LABELS: list[tuple[str, str]] = [
    # Best 5 first (used for 5-pack tier)
    ("Fayum Mummy Portraits", "Roman Egypt"),                       # 11
    ("Nebamun Hunting in the Marshes", "Ancient Egypt"),            # 01
    ("Alexander Mosaic", "Rome"),                                   # 08
    ("Achilles and Ajax Playing Dice Amphora", "Greece"),           # 05
    ("Ishtar Gate Reliefs", "Babylon"),                             # 13
    # Remaining 10
    ("Akhenaten and Nefertiti with their Children", "Egypt (Amarna)"),  # 02
    ("Book of the Dead of Hunefer", "Egypt"),                       # 03
    ("Tomb of Ramesses I Wall Paintings", "Egypt"),                 # 04
    ("The Berlin Painter Amphora", "Greece"),                       # 06
    ("The Francois Vase", "Greece"),                                # 07
    ("Villa of Livia Garden Room", "Rome"),                         # 09
    ("Pompeii Fresco of Bacchus", "Rome"),                          # 10
    ("Standard of Ur", "Mesopotamia"),                              # 12
    ("Ajanta Cave Paintings", "India"),                             # 14
    ("Han Dynasty Silk Paintings", "Ancient China"),                # 15
]
# Evolution of Portraits pack: 01 = first downloaded … 15 = last downloaded (see setup_evolution_portraits_pack.py)
EVOLUTION_PORTRAITS_PACK_LABELS: list[tuple[str, str]] = [
    # Best 5 first (used for 5-pack tier)
    ("Girl with a Pearl Earring", "Johannes Vermeer"),                   # 08
    ("Mona Lisa", "Leonardo da Vinci"),                                  # 05
    ("Marilyn Diptych", "Andy Warhol"),                                  # 15
    ("Self-Portrait with Thorn Necklace and Hummingbird", "Frida Kahlo"), # 14
    ("Self-Portrait with Bandaged Ear", "Vincent van Gogh"),             # 11
    # Remaining 10
    ("Fayum Mummy Portraits", "Roman Egypt"),                            # 01
    ("Nefertari in the Tomb of Nefertari", "Egypt"),                     # 02
    ("Portrait of a Young Woman", "Medieval"),                           # 03
    ("Christ Pantocrator", "Byzantine"),                                 # 04
    ("Portrait of Baldassare Castiglione", "Raphael"),                   # 06
    ("Self-Portrait", "Albrecht Dürer"),                                 # 07
    ("Self-Portrait with Two Circles", "Rembrandt"),                     # 09
    ("Portrait of Madame X", "John Singer Sargent"),                     # 10
    ("Les Demoiselles d'Avignon", "Pablo Picasso"),                      # 12
    ("Portrait of Dora Maar", "Pablo Picasso"),                          # 13
]
# Royalty & Power Portraits pack: 01 = first downloaded … 15 = last downloaded (see setup_royalty_portraits_pack.py)
ROYALTY_PORTRAITS_PACK_LABELS: list[tuple[str, str]] = [
    # Best 5 first (used for 5-pack tier)
    ("Napoleon Crossing the Alps", "Jacques-Louis David"),                    # 01
    ("Portrait of Henry VIII", "Hans Holbein the Younger"),                   # 03
    ("Portrait of Emperor Rudolf II as Vertumnus", "Giuseppe Arcimboldo"),    # 12
    ("Portrait of Louis XIV", "Hyacinthe Rigaud"),                            # 02
    ("The Blue Boy", "Thomas Gainsborough"),                                  # 09
    # Remaining 10
    ("Queen Elizabeth I Armada Portrait", "George Gower"),                    # 04
    ("Equestrian Portrait of Charles I", "Anthony van Dyck"),                 # 05
    ("Portrait of Pope Innocent X", "Diego Velázquez"),                       # 06
    ("Philip IV in Brown and Silver", "Diego Velázquez"),                     # 07
    ("Portrait of Madame de Pompadour", "François Boucher"),                  # 08
    ("Portrait of the Duke of Wellington", "Francisco Goya"),                 # 10
    ("Self-Portrait as a Nobleman", "Lorenzo Lippi"),                         # 11
    ("Emperor Qianlong in Court Dress", "Giuseppe Castiglione"),              # 13
    ("Shah Jahan on a Terrace", "Mughal School"),                             # 14
    ("Portrait of Empress Catherine II", "Fyodor Rokotov"),                   # 15
]

# Detailed style prompts for OpenAI (mode="prompt"). One per artwork; preserve face/identity.
# Each prompt explicitly describes brushwork, color palette, and technique for accurate results.
# Verified 2025-02: prompts match actual images in Masters pack.
MASTERS_PACK_PROMPTS: list[str] = [
    # Best 5 first (used for 5-pack tier)
    "in the style of Leonardo da Vinci's Mona Lisa: sfumato—soft, blended strokes with no hard edges, muted earth palette (umber, ochre, olive green), warm golden-brown skin tones, hazy atmospheric background. Preserve the subject's face and identity.",
    "in the style of Edvard Munch's The Scream: swirling, wavy brushstrokes in sky, orange and yellow undulating sky, blue-green water, distorted perspective, expressionist anxiety. Preserve the subject's face and identity.",
    "in the style of Salvador Dalí's The Persistence of Memory: smooth, meticulous brushwork, soft melting forms, warm desert palette (sand, blue sky), surrealist dreamscape. Preserve the subject's face and identity.",
    "in the style of Michelangelo's The Creation of Adam: fresco technique with soft, blended brushwork, warm flesh tones (peach, terracotta), cool blue-grey background, idealized Renaissance anatomy, divine touch gesture. Preserve the subject's face, identity, and likeness.",
    "in the style of Vincent van Gogh's Sunflowers: thick impasto brushstrokes in visible directions, vibrant yellows and ochres, green stems, textured paint surface, post-impressionist. Preserve the subject's face and identity.",
    # Remaining 10
    "in the style of Piet Mondrian's geometric abstraction: flat, hard-edge color blocks, primary palette (red, yellow, blue) on white, black grid lines, no brush texture—clean geometric planes. Preserve the subject's face and likeness.",
    "in the style of Francisco Goya's The Third of May 1808: dramatic chiaroscuro, dark browns and blacks, stark white shirt, warm lantern light, loose brushwork for crowd, tight detail on central figure. Preserve the subject's face and identity.",
    "in the style of Caravaggio's Judith Beheading Holofernes: tenebrist lighting—deep black shadows, single light source, rich red fabric, creamy flesh tones, precise brushwork on faces. Preserve the subject's face and likeness.",
    "in the style of Rembrandt's The Night Watch: Dutch Golden Age chiaroscuro, warm amber and browns, golden highlights on faces, deep shadows, visible brushwork, group portrait composition. Preserve the subject's face and identity.",
    "in the style of Diego Velázquez's Las Meninas: Spanish Baroque, layered brushwork, warm greys and browns, cream and gold fabrics, complex mirror composition, court portrait. Preserve the subject's face and likeness.",
    "in the style of Rembrandt's chiaroscuro portraits: thick impasto in lit areas, smooth blending in shadows, warm amber and umber palette, deep black backgrounds, visible brush marks on skin. Preserve the subject's face and identity.",
    "in the style of Wassily Kandinsky's Composition VIII: flat geometric shapes, primary colors (red, blue, yellow) plus black and white, crisp edges, abstract circles and lines, no realistic texture. Preserve the subject's face and likeness.",
    "in the style of Claude Monet's Impression, Sunrise: short, broken brushstrokes, orange and pink sunrise, blue-grey harbor, soft hazy atmosphere, loose impressionist technique. Preserve the subject's face and identity.",
    "in the style of Pierre-Auguste Renoir's Luncheon of the Boating Party: soft, blended impressionist strokes, warm skin tones, white and cream fabrics, dappled sunlight, vibrant blues and greens. Preserve the subject's face and likeness.",
    "in the style of Pablo Picasso's Les Demoiselles d'Avignon: angular geometric planes, ochre and pink palette, African mask influence, fragmented cubist forms, bold outlines. Preserve the subject's face and likeness.",
]
# Impression & Color pack: verified 2025-02 - prompts match actual images.
IMPRESSION_COLOR_PACK_PROMPTS: list[str] = [
    # Best 5 first (used for 5-pack tier)
    "in the style of Vincent van Gogh's Starry Night: thick swirling impasto strokes, deep cobalt blue sky, bright yellow and orange stars, swirling cypress in dark green, visible brush texture throughout. Preserve the subject's face and identity.",
    "in the style of Claude Monet's Water Lilies: soft, broken brushstrokes, pastel greens and pinks, lavender reflections on water, dappled light, no hard edges. Preserve the subject's face and likeness.",
    "in the style of Vincent van Gogh's night city scenes: short thick brushstrokes, warm yellows and oranges for street lamps, deep blue night sky, cobblestone texture. Preserve the subject's face and identity.",
    "in the style of Vincent van Gogh's Irises: thick directional brushstrokes, vibrant blues and purples, green foliage, yellow accents, expressive texture. Preserve the subject's face and likeness.",
    "in the style of Pierre-Auguste Renoir's Bal du moulin de la Galette: impressionist dappled light, warm skin tones, blue and white dresses, outdoor cafe. Preserve the subject's face and identity.",
    # Remaining 10
    "in the style of Edgar Degas's ballet class: soft pastel brushwork, peach and cream tones, tutus in white and pink, rehearsal studio atmosphere. Preserve the subject's face and identity.",
    "in the style of Paul Gauguin's Where Do We Come From: flat color blocks, Tahitian palette (rich greens, oranges, golds), bold outlines, simplified forms. Preserve the subject's face and likeness.",
    "in the style of Claude Monet's Woman with a Parasol: loose impressionist strokes, sky blue and white, soft greens, dappled sunlight, flowing dress. Preserve the subject's face and identity.",
    "in the style of Claude Monet's Japanese Bridge: wisteria purples and greens, arched bridge, water lily pond, soft blended strokes. Preserve the subject's face and likeness.",
    "in the style of Claude Monet's Impression, Sunrise: short strokes, orange and pink sun, blue-grey harbor, hazy atmosphere. Preserve the subject's face and identity.",
    "in the style of Paul Cézanne's Mont Sainte-Victoire: structured brushwork, geometric planes, ochre and blue palette, post-impressionist. Preserve the subject's face and identity.",
    "in the style of Pierre-Auguste Renoir's Luncheon of the Boating Party: soft blended strokes, warm skin tones, white and cream, dappled sunlight. Preserve the subject's face and likeness.",
    "in the style of Pierre-Auguste Renoir's The Swing: soft forest greens, dappled light, woman in white dress. Preserve the subject's face and likeness.",
    "in the style of Vincent van Gogh's Café Terrace at Night: bright yellow awning, starry blue sky, warm orange cafe glow, cobblestone, thick brushstrokes. Preserve the subject's face and likeness.",
    "in the style of Vincent van Gogh's Sunflowers: thick impasto brushstrokes, vibrant yellows and ochres, green stems, textured paint. Preserve the subject's face and identity.",
]
MODERN_ABSTRACT_PACK_PROMPTS: list[str] = [
    # Best 5 first (used for 5-pack tier)
    "in the style of Edvard Munch's The Scream: swirling orange and yellow sky, blue water, expressionist distortion. Preserve the subject's face and identity.",
    "in the style of Salvador Dalí's Persistence of Memory: smooth melting forms, warm desert palette, surrealist. Preserve the subject's face and likeness.",
    "in the style of Jackson Pollock's drip painting: splattered and dripped paint lines, black and white with color accents, energetic web, abstract expressionist. Preserve the subject's face and identity.",
    "in the style of Mark Rothko's color fields: large blocks of color, soft blurred edges, orange and yellow or warm tones, contemplative. Preserve the subject's face and likeness.",
    "in the style of Pablo Picasso's Les Demoiselles d'Avignon: angular geometric planes, ochre and pink, proto-cubist. Preserve the subject's face and identity.",
    # Remaining 10
    "in the style of Wassily Kandinsky's Composition VIII: flat geometric shapes, primary colors (red, blue, yellow) plus black, crisp edges, circles and abstract forms. Preserve the subject's face and identity.",
    "in the style of Kazimir Malevich's Black Square: suprematist, geometric shapes, black on white, bold contrast, minimal. Preserve the subject's face and likeness.",
    "in the style of Piet Mondrian's Broadway Boogie Woogie: grid of primary colors, yellow, red, blue squares, black lines, geometric. Preserve the subject's face and identity.",
    "in the style of Willem de Kooning's Woman I: aggressive brushwork, flesh pinks and yellows, distorted forms, abstract expressionist. Preserve the subject's face and likeness.",
    "in the style of Ernst Ludwig Kirchner's Street Dresden: angular brushstrokes, bold pink and purple, yellow and green, German expressionist urban. Preserve the subject's face and identity.",
    "in the style of Franz Marc's Blue Horse I: bold blue animal form, expressionist, geometric simplification. Preserve the subject's face and likeness.",
    "in the style of René Magritte's The Lovers: smooth surrealist brushwork, cloth draped over faces, mysterious. Preserve the subject's face and likeness.",
    "in the style of Salvador Dalí's The Elephants: surrealist, elongated legs, dreamlike desert, meticulous detail. Preserve the subject's face and identity.",
    "in the style of Georges Braque's Cubism: fragmented geometric planes, muted browns and greys, analytical cubist. Preserve the subject's face and identity.",
    "in the style of Pablo Picasso's Girl with a Mandolin: cubist geometric planes, ochre and brown palette, fragmented forms. Preserve the subject's face and likeness.",
]
ANCIENT_WORLDS_PACK_PROMPTS: list[str] = [
    # Best 5 first (used for 5-pack tier)
    "in the style of Fayum mummy portraits: encaustic wax, Roman Egypt, realistic faces, warm skin tones. Preserve the subject's face and identity.",
    "in the style of Ancient Egyptian tomb painting: flat figures in profile, warm earth tones (ochre, terracotta), black outlines, hieroglyphic aesthetic. Preserve the subject's face and identity.",
    "in the style of Roman Alexander Mosaic: tessellated stone, battle scene, warm earth tones. Preserve the subject's face and likeness.",
    "in the style of Greek black-figure pottery: black figures on red clay, mythological scenes, amphora form. Preserve the subject's face and identity.",
    "in the style of Babylonian Ishtar Gate: blue glaze tiles, lion relief, turquoise and gold. Preserve the subject's face and identity.",
    # Remaining 10
    "in the style of Amarna period Egyptian art: elongated forms, warm gold and blue, sun disk motifs, naturalistic. Preserve the subject's face and likeness.",
    "in the style of Egyptian Book of the Dead: papyrus cream background, flat figures, red and black ink, symbolic imagery. Preserve the subject's face and identity.",
    "in the style of Egyptian tomb wall paintings: Ramesside period, warm ochre and blue, ceremonial scenes. Preserve the subject's face and likeness.",
    "in the style of Greek red-figure pottery: red figures on black, elegant line work, classical. Preserve the subject's face and likeness.",
    "in the style of Greek Francois Vase: black-figure, narrative friezes, terracotta. Preserve the subject's face and identity.",
    "in the style of Roman Villa of Livia fresco: garden room, lush green foliage, naturalistic, warm stone. Preserve the subject's face and identity.",
    "in the style of Pompeii fresco: Bacchus, Roman wall painting, warm red and ochre. Preserve the subject's face and likeness.",
    "in the style of Mesopotamian Standard of Ur: lapis lazuli blue, gold, mosaic panels. Preserve the subject's face and likeness.",
    "in the style of Ajanta cave paintings: Indian Buddhist, flowing lines, rich reds and greens. Preserve the subject's face and likeness.",
    "in the style of Han Dynasty silk paintings: delicate brushwork, muted earth tones, flowing. Preserve the subject's face and identity.",
]
EVOLUTION_PORTRAITS_PACK_PROMPTS: list[str] = [
    # Best 5 first (used for 5-pack tier)
    "in the style of Johannes Vermeer's Girl with a Pearl Earring: soft diffused light, pearl earring, blue and yellow turban. Preserve the subject's face and likeness.",
    "in the style of Leonardo da Vinci's Mona Lisa: sfumato soft blending, muted earth tones, enigmatic smile. Preserve the subject's face and identity.",
    "in the style of Andy Warhol's Marilyn: Pop Art screen print, bold pink and yellow, repeated image. Preserve the subject's face and identity.",
    "in the style of Frida Kahlo's self-portrait: thorn necklace, Mexican folk colors, symbolic. Preserve the subject's face and likeness.",
    "in the style of Vincent van Gogh's self-portrait: bandaged ear, thick directional brushstrokes, greens and ochres. Preserve the subject's face and identity.",
    # Remaining 10
    "in the style of Fayum mummy portraits: encaustic wax, Roman Egypt, realistic faces, warm skin tones, dark eyes. Preserve the subject's face and identity.",
    "in the style of Egyptian tomb of Nefertari: warm ochre and blue, flat figures, hieroglyphic aesthetic. Preserve the subject's face and likeness.",
    "in the style of Medieval portrait: flat iconic style, gold leaf background, rich blues and reds. Preserve the subject's face and identity.",
    "in the style of Byzantine Christ Pantocrator: gold background, solemn face, dark robes, iconic. Preserve the subject's face and likeness.",
    "in the style of Raphael's portrait: Renaissance soft modeling, warm skin, dark background. Preserve the subject's face and likeness.",
    "in the style of Albrecht Dürer's self-portrait: Northern Renaissance, meticulous detail, fur collar. Preserve the subject's face and identity.",
    "in the style of Rembrandt's self-portrait: chiaroscuro, warm amber and brown, thick brushwork in light. Preserve the subject's face and identity.",
    "in the style of John Singer Sargent's Madame X: elegant black dress, pale skin, dramatic pose. Preserve the subject's face and likeness.",
    "in the style of Pablo Picasso's Les Demoiselles: proto-cubist angular planes, ochre and pink. Preserve the subject's face and likeness.",
    "in the style of Pablo Picasso's portrait of Dora Maar: cubist fragmented planes, muted palette. Preserve the subject's face and identity.",
]
ROYALTY_PORTRAITS_PACK_PROMPTS: list[str] = [
    # Best 5 first (used for 5-pack tier)
    "in the style of Jacques-Louis David's Napoleon Crossing the Alps: neoclassical, heroic equestrian, red cape, grey horse, dramatic sky. Preserve the subject's face and identity.",
    "in the style of Hans Holbein's Henry VIII: Tudor portrait, rich red and gold fabrics, imposing. Preserve the subject's face and identity.",
    "in the style of Giuseppe Arcimboldo's Vertumnus: composite portrait, fruits and vegetables, autumn palette. Preserve the subject's face and likeness.",
    "in the style of Hyacinthe Rigaud's Louis XIV: baroque, royal blue and gold, ermine, grand pose. Preserve the subject's face and likeness.",
    "in the style of Thomas Gainsborough's Blue Boy: blue satin costume, aristocratic, 18th century. Preserve the subject's face and identity.",
    # Remaining 10
    "in the style of Elizabethan Armada portrait: jeweled, pearl necklace, black dress, royal. Preserve the subject's face and likeness.",
    "in the style of Anthony van Dyck's equestrian portrait: baroque, noble pose, rich fabrics. Preserve the subject's face and identity.",
    "in the style of Diego Velázquez's Pope Innocent X: baroque chiaroscuro, red silk, dramatic lighting. Preserve the subject's face and likeness.",
    "in the style of Velázquez's Philip IV: Spanish court, brown and silver, rich fabrics. Preserve the subject's face and identity.",
    "in the style of François Boucher's Madame de Pompadour: rococo, pastel pink and blue, decorative. Preserve the subject's face and likeness.",
    "in the style of Francisco Goya's portrait: Spanish master, dark brown tones, psychological. Preserve the subject's face and likeness.",
    "in the style of Lorenzo Lippi's nobleman portrait: baroque, aristocratic, dark background. Preserve the subject's face and identity.",
    "in the style of Giuseppe Castiglione's Qianlong: Chinese-European fusion, imperial yellow, detailed. Preserve the subject's face and identity.",
    "in the style of Mughal miniature Shah Jahan: jewel tones, intricate detail, lapis and gold. Preserve the subject's face and likeness.",
    "in the style of Fyodor Rokotov's Catherine II: Russian imperial, elegant, soft brushwork. Preserve the subject's face and identity.",
]

# Verify alignment: PACK_PATHS[i] -> PACK_LABELS[i] -> PACK_PROMPTS[i] (index i = file NN where NN = i+1)
def _verify_pack_alignment() -> None:
    packs = [
        (MASTERS_PACK_PATHS, MASTERS_PACK_LABELS, MASTERS_PACK_PROMPTS),
        (IMPRESSION_COLOR_PACK_PATHS, IMPRESSION_COLOR_PACK_LABELS, IMPRESSION_COLOR_PACK_PROMPTS),
        (MODERN_ABSTRACT_PACK_PATHS, MODERN_ABSTRACT_PACK_LABELS, MODERN_ABSTRACT_PACK_PROMPTS),
        (ANCIENT_WORLDS_PACK_PATHS, ANCIENT_WORLDS_PACK_LABELS, ANCIENT_WORLDS_PACK_PROMPTS),
        (EVOLUTION_PORTRAITS_PACK_PATHS, EVOLUTION_PORTRAITS_PACK_LABELS, EVOLUTION_PORTRAITS_PACK_PROMPTS),
        (ROYALTY_PORTRAITS_PACK_PATHS, ROYALTY_PORTRAITS_PACK_LABELS, ROYALTY_PORTRAITS_PACK_PROMPTS),
    ]
    for paths, labels, prompts in packs:
        n = len(paths)
        if len(labels) != n or len(prompts) != n:
            logger.error("Pack alignment error: paths=%d labels=%d prompts=%d", n, len(labels), len(prompts))


# Map style_id to paths, labels, and pack names (for marketing selector)
_STYLE_ID_TO_PATHS: dict[int, list[str]] = {
    STYLE_ID_MASTERS_PACK: MASTERS_PACK_PATHS,
    STYLE_ID_IMPRESSION_COLOR_PACK: IMPRESSION_COLOR_PACK_PATHS,
    STYLE_ID_MODERN_ABSTRACT_PACK: MODERN_ABSTRACT_PACK_PATHS,
    STYLE_ID_ANCIENT_WORLDS_PACK: ANCIENT_WORLDS_PACK_PATHS,
    STYLE_ID_EVOLUTION_PORTRAITS_PACK: EVOLUTION_PORTRAITS_PACK_PATHS,
    STYLE_ID_ROYALTY_PORTRAITS_PACK: ROYALTY_PORTRAITS_PACK_PATHS,
}
_STYLE_ID_TO_LABELS: dict[int, list[tuple[str, str]]] = {
    STYLE_ID_MASTERS_PACK: MASTERS_PACK_LABELS,
    STYLE_ID_IMPRESSION_COLOR_PACK: IMPRESSION_COLOR_PACK_LABELS,
    STYLE_ID_MODERN_ABSTRACT_PACK: MODERN_ABSTRACT_PACK_LABELS,
    STYLE_ID_ANCIENT_WORLDS_PACK: ANCIENT_WORLDS_PACK_LABELS,
    STYLE_ID_EVOLUTION_PORTRAITS_PACK: EVOLUTION_PORTRAITS_PACK_LABELS,
    STYLE_ID_ROYALTY_PORTRAITS_PACK: ROYALTY_PORTRAITS_PACK_LABELS,
}
_STYLE_ID_TO_PACK_NAME: dict[int, str] = {
    STYLE_ID_MASTERS_PACK: "Masters",
    STYLE_ID_IMPRESSION_COLOR_PACK: "Impression & Color",
    STYLE_ID_MODERN_ABSTRACT_PACK: "Modern & Abstract",
    STYLE_ID_ANCIENT_WORLDS_PACK: "Ancient Worlds",
    STYLE_ID_EVOLUTION_PORTRAITS_PACK: "Evolution of Portraits",
    STYLE_ID_ROYALTY_PORTRAITS_PACK: "Royalty & Power",
}
# Map style_id to prompts list for URL-to-prompt resolution
_STYLE_ID_TO_PROMPTS: dict[int, list[str]] = {
    STYLE_ID_MASTERS_PACK: MASTERS_PACK_PROMPTS,
    STYLE_ID_IMPRESSION_COLOR_PACK: IMPRESSION_COLOR_PACK_PROMPTS,
    STYLE_ID_MODERN_ABSTRACT_PACK: MODERN_ABSTRACT_PACK_PROMPTS,
    STYLE_ID_ANCIENT_WORLDS_PACK: ANCIENT_WORLDS_PACK_PROMPTS,
    STYLE_ID_EVOLUTION_PORTRAITS_PACK: EVOLUTION_PORTRAITS_PACK_PROMPTS,
    STYLE_ID_ROYALTY_PORTRAITS_PACK: ROYALTY_PORTRAITS_PACK_PROMPTS,
}
_verify_pack_alignment()


_BRUSHWORK_PHRASE = (
    " CRITICAL: Replicate the exact brushwork, stroke direction, paint texture, and color palette "
    "of the original painting. Use visible brushstrokes matching the painting's technique—impasto "
    "where thick, smooth blending where soft. Match the original's color temperature and palette. "
    "The result must look like an actual oil painting with authentic brush marks and surface quality. "
)

def _style_url_to_prompt(style_url: str, style_id: int) -> str:
    """Parse style URL to get 1-based index, return the corresponding style prompt.
    Critical: index from URL must match PACK_PATHS order (01=first, 02=second, ...).
    """
    # Match paths like .../styles/masters/masters-01.jpg or .../impression-color-05.jpg
    match = re.search(r"/styles/([^/]+)/\1-(\d{2})\.(?:jpg|jpeg|png|webp)", style_url, re.I)
    if not match:
        match = re.search(r"/([a-z0-9-]+)-(\d{2})\.(?:jpg|jpeg|png|webp)", style_url, re.I)
    if not match:
        logger.warning("Could not parse style index from URL: %s", (style_url or "")[:80])
        return "in the style of classical portrait painting." + _BRUSHWORK_PHRASE + "Preserve the subject's face and identity."
    index_str = match.group(2)
    idx = int(index_str)  # 1-based (01 -> 1)
    prompts = _STYLE_ID_TO_PROMPTS.get(style_id)
    if not prompts or idx < 1 or idx > len(prompts):
        logger.warning("Style index %d out of range for style_id %s (prompts len=%d)", idx, style_id, len(prompts or []))
        return "in the style of classical portrait painting." + _BRUSHWORK_PHRASE + "Preserve the subject's face and identity."
    base = prompts[idx - 1]
    # Insert brushwork phrase before "Preserve" (prompts end with ". Preserve the subject's...")
    return base.replace(". Preserve", "." + _BRUSHWORK_PHRASE + "Preserve")


def _build_result_labels(
    order: Order, result_urls_list: list[str], styles: list
) -> list[tuple[str, str]]:
    """Build (painting_title, artist) for each result image for the ready email."""
    n = len(result_urls_list)
    if not n:
        return []
    if order.style_id == STYLE_ID_MASTERS_PACK:
        return MASTERS_PACK_LABELS[:n]
    if order.style_id == STYLE_ID_IMPRESSION_COLOR_PACK:
        return IMPRESSION_COLOR_PACK_LABELS[:n]
    if order.style_id == STYLE_ID_MODERN_ABSTRACT_PACK:
        return MODERN_ABSTRACT_PACK_LABELS[:n]
    if order.style_id == STYLE_ID_ANCIENT_WORLDS_PACK:
        return ANCIENT_WORLDS_PACK_LABELS[:n]
    if order.style_id == STYLE_ID_EVOLUTION_PORTRAITS_PACK:
        return EVOLUTION_PORTRAITS_PACK_LABELS[:n]
    if order.style_id == STYLE_ID_ROYALTY_PORTRAITS_PACK:
        return ROYALTY_PORTRAITS_PACK_LABELS[:n]
    style_data = next((s for s in styles if s.get("id") == order.style_id), None)
    title = order.style_name or (style_data.get("title") if style_data else "Stil")
    artist = style_data.get("artist", "Artist") if style_data else "Artist"
    return [(title, artist)] * n


def _load_styles_data() -> list:
    styles_file = Path(__file__).parent / "static" / "landing" / "styles-data.js"
    if not styles_file.exists():
        return []
    content = styles_file.read_text(encoding="utf-8")
    start = content.find("[")
    end = content.rfind("]") + 1
    if start < 0 or end <= start:
        return []
    return json.loads(content[start:end])


# ── Marketing API ─────────────────────────────────────────────

VALID_STYLE_IDS = frozenset({
    STYLE_ID_MASTERS_PACK,
    STYLE_ID_IMPRESSION_COLOR_PACK,
    STYLE_ID_MODERN_ABSTRACT_PACK,
    STYLE_ID_ANCIENT_WORLDS_PACK,
    STYLE_ID_EVOLUTION_PORTRAITS_PACK,
    STYLE_ID_ROYALTY_PORTRAITS_PACK,
})


@app.get("/api/marketing/styles")
async def get_marketing_styles() -> JSONResponse:
    """Return all 90 paintings for the marketing style selector."""
    items = []
    for style_id, paths in _STYLE_ID_TO_PATHS.items():
        pack_name = _STYLE_ID_TO_PACK_NAME.get(style_id, "")
        labels = _STYLE_ID_TO_LABELS.get(style_id, [])
        for idx, path in enumerate(paths):
            style_index = idx + 1
            title, artist = labels[idx] if idx < len(labels) else ("", "")
            style_image_url = _resolve_style_image_url(path)
            items.append({
                "style_id": style_id,
                "style_index": style_index,
                "pack_name": pack_name,
                "title": title,
                "artist": artist,
                "style_image_url": style_image_url,
            })
    return JSONResponse(items)


@app.post("/api/marketing/style-transfer")
async def marketing_style_transfer(
    image: UploadFile = File(...),
    style_id: int = Form(...),
    style_index: int = Form(...),
) -> Response:
    """
    Single high-quality style transfer for marketing. Returns image bytes.
    Uses quality=high (OpenAI) or output_quality=95 (Replicate).
    """
    if style_id not in VALID_STYLE_IDS:
        raise HTTPException(status_code=400, detail="Invalid style_id (must be 13-18)")
    if style_index < 1 or style_index > 15:
        raise HTTPException(status_code=400, detail="style_index must be 1-15")

    if not image.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    ext = Path(image.filename).suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}")

    content = await image.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File must be under 10 MB")

    upload_id = uuid.uuid4().hex[:12]
    upload_dir = get_upload_dir() / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"photo{ext}"
    file_path.write_bytes(content)

    settings = get_settings()
    if settings.public_base_url:
        image_url = _build_public_upload_url(upload_id, ext)
    else:
        image_url = _upload_to_litterbox(str(file_path), f"photo{ext}")

    paths = _STYLE_ID_TO_PATHS.get(style_id)
    if not paths or style_index > len(paths):
        raise HTTPException(status_code=400, detail="Invalid style_index for pack")
    style_path = paths[style_index - 1]
    style_url = _resolve_style_image_url(style_path)
    if not style_url or not style_url.startswith("https://"):
        raise HTTPException(
            status_code=500,
            detail="PUBLIC_BASE_URL must be set so style images are accessible via HTTPS",
        )

    style_prompt = _style_url_to_prompt(style_url, style_id)
    service = get_service()

    def _run_transfer() -> tuple:
        return service.transfer_style_sync(
            image_url=image_url,
            style_image_url=style_url,
            structure_denoising_strength=0.7,
            style_prompt=style_prompt,
            prompt_suffix=None,
            quality="high",
            output_quality=95,
        )

    result, job_id = await asyncio.to_thread(_run_transfer)

    if isinstance(result, dict) and "content" in result:
        image_bytes = result["content"]
        content_type = result.get("content_type", "image/jpeg")
    else:
        result_url = str(result)
        with httpx.Client(timeout=60) as client:
            r = client.get(result_url)
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail="Failed to fetch style transfer result")
        image_bytes = r.content
        content_type = r.headers.get("content-type", "image/jpeg").split(";")[0].strip()

    if content_type not in ("image/jpeg", "image/png", "image/webp"):
        content_type = "image/jpeg"
    return Response(content=image_bytes, media_type=content_type)


# ── Order endpoints ──────────────────────────────────────────

@app.post("/api/orders", response_model=OrderResponse, status_code=201)
async def create_order(
    order_data: OrderCreateRequest,
    db: Session = Depends(get_db),
) -> OrderResponse:
    style_data = None
    try:
        styles = _load_styles_data()
        style_data = next((s for s in styles if s.get("id") == order_data.style_id), None)
    except Exception as e:
        logger.warning(f"Could not load style data: {e}")

    # Reject orders for Coming Soon / unavailable styles
    UNAVAILABLE_STYLE_IDS = (STYLE_ID_ANCIENT_WORLDS_PACK, STYLE_ID_EVOLUTION_PORTRAITS_PACK, STYLE_ID_ROYALTY_PORTRAITS_PACK)
    if order_data.style_id in UNAVAILABLE_STYLE_IDS:
        raise HTTPException(
            status_code=400,
            detail="Acest pachet de stiluri nu este disponibil momentan. Te rugăm să alegi alt stil.",
        )

    order_id = f"ART-{int(datetime.utcnow().timestamp() * 1000)}-{uuid.uuid4().hex[:8].upper()}"

    style_image_url = _resolve_style_image_url(style_data.get("styleImageUrl") if style_data else None)
    style_image_urls = None
    if order_data.style_id == STYLE_ID_MASTERS_PACK:
        style_image_urls = json.dumps([_resolve_style_image_url(p) for p in MASTERS_PACK_PATHS])
        if not style_image_url:
            style_image_url = _resolve_style_image_url(MASTERS_PACK_PATHS[0])
    elif order_data.style_id == STYLE_ID_IMPRESSION_COLOR_PACK:
        style_image_urls = json.dumps([_resolve_style_image_url(p) for p in IMPRESSION_COLOR_PACK_PATHS])
        if not style_image_url:
            style_image_url = _resolve_style_image_url(IMPRESSION_COLOR_PACK_PATHS[0])
    elif order_data.style_id == STYLE_ID_MODERN_ABSTRACT_PACK:
        style_image_urls = json.dumps([_resolve_style_image_url(p) for p in MODERN_ABSTRACT_PACK_PATHS])
        if not style_image_url:
            style_image_url = _resolve_style_image_url(MODERN_ABSTRACT_PACK_PATHS[0])
    elif order_data.style_id == STYLE_ID_ANCIENT_WORLDS_PACK:
        style_image_urls = json.dumps([_resolve_style_image_url(p) for p in ANCIENT_WORLDS_PACK_PATHS])
        if not style_image_url:
            style_image_url = _resolve_style_image_url(ANCIENT_WORLDS_PACK_PATHS[0])
    elif order_data.style_id == STYLE_ID_EVOLUTION_PORTRAITS_PACK:
        style_image_urls = json.dumps([_resolve_style_image_url(p) for p in EVOLUTION_PORTRAITS_PACK_PATHS])
        if not style_image_url:
            style_image_url = _resolve_style_image_url(EVOLUTION_PORTRAITS_PACK_PATHS[0])
    elif order_data.style_id == STYLE_ID_ROYALTY_PORTRAITS_PACK:
        style_image_urls = json.dumps([_resolve_style_image_url(p) for p in ROYALTY_PORTRAITS_PACK_PATHS])
        if not style_image_url:
            style_image_url = _resolve_style_image_url(ROYALTY_PORTRAITS_PACK_PATHS[0])
    # Limit to first 5 images for pack_tier 5 (9.99 Lei)
    pack_tier = order_data.pack_tier if order_data.pack_tier in (5, 15) else 5
    if style_image_urls and pack_tier == 5:
        urls_list = json.loads(style_image_urls)
        style_image_urls = json.dumps(urls_list[:5])
    amount = 9.99 if pack_tier == 5 else 19.99
    # Fail fast if style URLs are not public HTTPS (Replicate requires this)
    def _must_be_https(name: str, url: Optional[str]) -> None:
        if not url or not url.strip():
            return
        if not url.strip().startswith("https://"):
            logger.warning(
                "Style URL not HTTPS at order creation; PUBLIC_BASE_URL may be unset. resolved=%s",
                (url or "")[:80],
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    "Server configuration error: PUBLIC_BASE_URL must be set so we can process your artwork. "
                    "Please try again in a moment or contact support."
                ),
            )

    _must_be_https("style_image_url", style_image_url)
    if order_data.image_url and not order_data.image_url.strip().startswith("https://"):
        logger.warning("Order image_url not HTTPS: %s", order_data.image_url[:80])
        raise HTTPException(
            status_code=400,
            detail="The uploaded photo URL must be a secure (HTTPS) link. Please upload your photo again.",
        )

    portrait_mode = (order_data.portrait_mode or "realistic").strip().lower()
    if portrait_mode not in ("realistic", "artistic"):
        portrait_mode = "realistic"

    order = Order(
        order_id=order_id,
        status=OrderStatus.PENDING.value,
        email=order_data.email,
        style_id=order_data.style_id,
        style_name=style_data.get("title") if style_data else None,
        image_url=order_data.image_url,
        portrait_mode=portrait_mode,
        style_image_url=style_image_url,
        style_image_urls=style_image_urls,
        amount=amount,
        billing_name=order_data.billing_name,
        billing_address=order_data.billing_address,
        billing_city=order_data.billing_city,
        billing_state=order_data.billing_state,
        billing_zip=order_data.billing_zip,
        billing_country=order_data.billing_country,
    )

    db.add(order)
    db.commit()
    db.refresh(order)
    logger.info(f"Order created: {order_id} for {order_data.email}")

    # Persist customer upload into DB so style transfer still has the image after redeploy
    if _is_our_upload_url(order_data.image_url):
        parsed = _parse_upload_id_and_filename(order_data.image_url)
        if parsed:
            upload_id, filename = parsed
            file_path = get_upload_dir() / upload_id / filename
            if file_path.exists() and file_path.is_file():
                try:
                    content = file_path.read_bytes()
                    ext = Path(filename).suffix.lower()
                    content_type = "image/jpeg" if ext in (".jpg", ".jpeg") else f"image/{ext[1:]}"
                    if ext == ".png":
                        content_type = "image/png"
                    elif ext == ".webp":
                        content_type = "image/webp"
                    row = OrderSourceImage(
                        order_id=order_id,
                        content_type=content_type,
                        data=content,
                    )
                    db.merge(row)
                    db.commit()
                    logger.info("Order %s: persisted source image from upload %s", order_id, upload_id)
                except Exception as e:
                    logger.warning("Order %s: could not persist source image: %s", order_id, e)
            else:
                logger.warning("Order %s: upload file missing at %s (redeploy?)", order_id, file_path)

    return OrderResponse.model_validate(order)


@app.get("/api/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, db: Session = Depends(get_db)) -> OrderResponse:
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderResponse.model_validate(order)


@app.get("/api/orders/{order_id}/status", response_model=OrderStatusResponse)
async def get_order_status(order_id: str, db: Session = Depends(get_db)) -> OrderStatusResponse:
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    labels = None
    style_name = order.style_name
    style_image_urls_out = order.style_image_urls
    if order.status == "completed" and order.result_urls:
        try:
            urls = json.loads(order.result_urls)
            if urls:
                styles = _load_styles_data()
                labels_tuples = _build_result_labels(order, urls, styles)
                labels = [[t[0], t[1]] for t in labels_tuples]
                if not style_name and order.style_id and styles:
                    style_data = next((s for s in styles if s.get("id") == order.style_id), None)
                    if style_data:
                        style_name = style_data.get("title")
                # Ensure style_image_urls has same length and order as result_urls (1:1 mapping)
                if order.style_image_urls:
                    style_arr = json.loads(order.style_image_urls)
                    if isinstance(style_arr, list) and len(style_arr) != len(urls):
                        style_arr = style_arr[: len(urls)]
                        style_image_urls_out = json.dumps(style_arr)
        except Exception:
            pass

    return OrderStatusResponse(
        order_id=order.order_id,
        status=order.status,
        result_urls=order.result_urls,
        result_labels=labels,
        style_id=order.style_id,
        style_name=style_name,
        initial_image_url=order.image_url,
        style_image_urls=style_image_urls_out,
        replicate_prediction_details=order.replicate_prediction_details,
        error=order.style_transfer_error,
    )


@app.get("/api/orders/{order_id}/result/{index}")
async def get_order_result_image(order_id: str, index: int, db: Session = Depends(get_db)):
    """Single entry point for result images: DB first (14-day access, survives redeploy), then disk fallback."""
    if index < 1 or index > 20:
        raise HTTPException(status_code=400, detail="Invalid index")
    if "/" in order_id or "\\" in order_id or order_id in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid order id")
    # Prefer DB (survives redeploy)
    row = db.query(OrderResultImage).filter(
        OrderResultImage.order_id == order_id,
        OrderResultImage.image_index == index,
    ).first()
    if row:
        return Response(content=row.data, media_type=row.content_type)
    # Fallback: disk (legacy or if DB was cleared by TTL)
    results_dir = get_order_results_dir() / order_id
    for ext in ("jpg", "jpeg", "png", "webp"):
        path = results_dir / f"{index}.{ext}"
        if path.exists():
            return FileResponse(path, media_type=f"image/{ext}" if ext != "jpg" else "image/jpeg")
    raise HTTPException(status_code=404, detail="Image not available")


@app.get("/api/orders/{order_id}/source-image")
async def get_order_source_image(order_id: str, db: Session = Depends(get_db)):
    """Serve the customer's uploaded photo for this order (persisted at order creation; survives redeploy)."""
    if "/" in order_id or "\\" in order_id or order_id in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid order id")
    row = db.query(OrderSourceImage).filter(OrderSourceImage.order_id == order_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Source image not available")
    return Response(content=row.data, media_type=row.content_type)


@app.get("/api/orders/{order_id}/download-all")
async def download_all_results(order_id: str, db: Session = Depends(get_db)):
    """Download all generated images for an order as a zip file. Reads from DB first (14-day TTL)."""
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not order.result_urls:
        raise HTTPException(status_code=404, detail="No result images available yet")
    try:
        urls = json.loads(order.result_urls) if isinstance(order.result_urls, str) else (order.result_urls or [])
    except Exception:
        urls = []
    if not isinstance(urls, list) or not urls:
        raise HTTPException(status_code=404, detail="No result images available yet")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for i in range(1, len(urls) + 1):
            try:
                # Prefer DB (same source as /result/{index}; 14-day access)
                row = db.query(OrderResultImage).filter(
                    OrderResultImage.order_id == order_id,
                    OrderResultImage.image_index == i,
                ).first()
                if row:
                    ext = ".jpg" if "jpeg" in row.content_type else ".png" if "png" in row.content_type else ".webp" if "webp" in row.content_type else ".jpg"
                    zf.writestr(f"artify_{order_id}_{i:02d}{ext}", row.data)
                    continue
                # Fallback: fetch from URL (legacy or after TTL)
                u = urls[i - 1] if i <= len(urls) else None
                if not u:
                    continue
                resp = httpx.get(u, timeout=45)
                if resp.status_code >= 400:
                    continue
                ext = Path(urlparse(u).path).suffix or ".jpg"
                zf.writestr(f"artify_{order_id}_{i:02d}{ext}", resp.content)
            except Exception:
                continue
    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{order_id}-artify-images.zip"'},
    )


@app.post("/api/orders/{order_id}/pay")
async def pay_order(
    order_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != OrderStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Order already processed")

    body = await request.json()
    order.status = OrderStatus.PAID.value
    order.payment_status = "paid"
    order.payment_provider = body.get("payment_provider", "stripe")
    order.payment_transaction_id = body.get("transaction_id", "")
    order.paid_at = datetime.utcnow()
    db.commit()

    background_tasks.add_task(process_order_style_transfer, order_id)
    logger.info(f"Order paid, processing started: {order_id}")
    return {"status": "ok", "order_id": order_id}


async def process_order_style_transfer(order_id: str):
    """Run style transfers in a worker thread so API remains responsive."""
    if order_id in _ACTIVE_ORDER_TASKS:
        return
    _ACTIVE_ORDER_TASKS.add(order_id)
    try:
        await asyncio.to_thread(_run_style_transfer_sync, order_id)
    finally:
        _ACTIVE_ORDER_TASKS.discard(order_id)


def _run_style_transfer_sync(order_id: str) -> None:
    db = SessionLocal()
    lock_acquired = False
    try:
        lock_acquired = _try_acquire_order_lock_sync(db, order_id)
        if not lock_acquired:
            logger.info("Order %s is already being processed by another worker; skipping duplicate run", order_id)
            return

        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            logger.error(f"Order not found for processing: {order_id}")
            return

        style_urls = []
        if order.style_image_urls:
            try:
                style_urls = json.loads(order.style_image_urls) if isinstance(order.style_image_urls, str) else (order.style_image_urls or [])
            except (json.JSONDecodeError, TypeError):
                style_urls = []
        if not style_urls and order.style_image_url:
            style_urls = [order.style_image_url]
        if not style_urls:
            error_msg = "Style reference image missing"
            order.status = OrderStatus.FAILED.value
            order.style_transfer_error = error_msg
            order.failed_at = datetime.utcnow()
            db.commit()
            EmailService().send_order_failed(order_id, order.email, error_msg)
            return

        # Resume: if already processing with partial results, skip completed ones
        result_urls_list = []
        job_ids = []
        prediction_details = []
        skip = 0
        # Resume from any partial progress, regardless of current state string.
        # This prevents falling back to 1 image after restarts/retries.
        if order.result_urls:
            try:
                result_urls_list = json.loads(order.result_urls) if isinstance(order.result_urls, str) else (order.result_urls or [])
                job_ids = (order.style_transfer_job_id or "").split(",") if order.style_transfer_job_id else []
                if order.replicate_prediction_details:
                    prediction_details = json.loads(order.replicate_prediction_details) if isinstance(order.replicate_prediction_details, str) else (order.replicate_prediction_details or [])
                if isinstance(result_urls_list, list):
                    # Never reset completed/partial results; preserve deterministic ordering.
                    if len(result_urls_list) >= len(style_urls):
                        if order.status != OrderStatus.COMPLETED.value:
                            order.status = OrderStatus.COMPLETED.value
                            order.completed_at = order.completed_at or datetime.utcnow()
                            db.commit()
                        logger.info("Order %s already has all %d results; skipping", order_id, len(style_urls))
                        return
                    skip = len(result_urls_list)
                    job_ids = [x.strip() for x in job_ids if x.strip()][:skip]
                    prediction_details = prediction_details[:skip] if isinstance(prediction_details, list) else []
                    logger.info(f"Resuming order {order_id}: skipping {skip} done, {len(style_urls) - skip} remaining")
                else:
                    result_urls_list = []
                    job_ids = []
                    prediction_details = []
            except (json.JSONDecodeError, TypeError):
                result_urls_list = []
                job_ids = []
                prediction_details = []
                skip = 0

        try:
            order.status = OrderStatus.PROCESSING.value
            db.commit()

            # Use persisted source image URL if available (survives redeploy); else order.image_url
            source_image_url = order.image_url
            if db.query(OrderSourceImage).filter(OrderSourceImage.order_id == order_id).first():
                base = (get_settings().public_base_url or "").rstrip("/")
                if base:
                    source_image_url = f"{base}/api/orders/{order_id}/source-image"
                    logger.info("Order %s: using persisted source image URL for style transfer", order_id)

            service = get_service()
            settings = get_settings()
            use_openai = (settings.style_transfer_provider or "openai").strip().lower() == "openai"
            portrait_mode = (order.portrait_mode or "realistic").strip().lower()
            artistic_suffix = (
                " Make the result strongly artistic and painterly. Emphasize visible brushwork, "
                "bold impasto texture, and pronounced brushstrokes. The output must look like a "
                "real oil painting with thick, expressive paint application—not smooth or digital. "
                "Paint the subject fully in the style of this artwork: reimagine their clothing, "
                "setting, lighting, and pose as if they were an original subject of this painting. "
                "Take full artistic liberties to make the portrait feel authentically part of this "
                "artistic tradition—do not simply apply a filter, but truly render them as a "
                "painted subject in this style."
                if portrait_mode == "artistic" else None
            )
            remaining_style_urls = style_urls[skip:]
            replicate_fallback = get_replicate_service() if use_openai else None
            for i, style_url in enumerate(remaining_style_urls):
                if i > 0:
                    time.sleep(30)
                result_url, job_id = None, None
                provider_used = service
                style_prompt = _style_url_to_prompt(style_url, order.style_id) if use_openai else None
                max_openai_attempts = 3
                for attempt in range(max_openai_attempts):
                    try:
                        result_url, job_id = service.transfer_style_sync(
                            image_url=source_image_url,
                            style_image_url=style_url if not use_openai else None,
                            structure_denoising_strength=0.7,
                            style_prompt=style_prompt,
                            prompt_suffix=artistic_suffix,
                        )
                        break
                    except (StyleTransferTimeout, StyleTransferError) as e:
                        if attempt < max_openai_attempts - 1:
                            logger.warning(
                                "Style transfer failed for order %s image %d (attempt %d/%d), retrying in 10s: %s",
                                order_id, skip + i + 1, attempt + 1, max_openai_attempts, e,
                            )
                            time.sleep(10)
                            continue
                        # After 3 OpenAI failures: try Replicate fallback if available
                        if use_openai and replicate_fallback:
                            try:
                                logger.info(
                                    "OpenAI failed 3 times for order %s image %d; falling back to Replicate",
                                    order_id, skip + i + 1,
                                )
                                result_url, job_id = replicate_fallback.transfer_style_sync(
                                    image_url=source_image_url,
                                    style_image_url=style_url,
                                    structure_denoising_strength=0.7,
                                    style_prompt=None,
                                    prompt_suffix=artistic_suffix,
                                )
                                provider_used = replicate_fallback
                                break
                            except (StyleTransferTimeout, StyleTransferError) as fallback_err:
                                logger.warning(
                                    "Replicate fallback also failed for order %s image %d: %s",
                                    order_id, skip + i + 1, fallback_err,
                                )
                                raise fallback_err from e
                        raise
                result_urls_list.append(result_url)
                job_ids.append(job_id)
                result_url_for_pred = result_url if isinstance(result_url, str) else None
                try:
                    pred = provider_used.provider.get_prediction(job_id)
                    prediction_details.append({
                        "id": pred.get("id"),
                        "status": pred.get("status"),
                        "error": pred.get("error"),
                        "metrics": pred.get("metrics"),
                        "created_at": pred.get("created_at"),
                        "started_at": pred.get("started_at"),
                        "completed_at": pred.get("completed_at"),
                        "result_url": result_url_for_pred,
                        "model": pred.get("model"),
                        "version": pred.get("version"),
                        "source": pred.get("source"),
                        "data_removed": pred.get("data_removed"),
                        "urls": pred.get("urls"),
                        "logs": (pred.get("logs") or "")[:500] if pred.get("logs") else None,
                    })
                except Exception:
                    prediction_details.append({"id": job_id, "status": "succeeded", "result_url": result_url_for_pred})

                # Store serializable version (dicts with bytes can't be JSON-serialized)
                serializable = [x if isinstance(x, str) else "openai://pending" for x in result_urls_list]
                order.result_urls = json.dumps(serializable)
                order.style_transfer_job_id = ",".join(job_ids)
                order.replicate_prediction_details = json.dumps(prediction_details)
                db.commit()

            # Persist images to our storage so URLs don't expire (Replicate links are temporary)
            result_urls_list = _persist_result_images(order_id, result_urls_list)
            order.result_urls = json.dumps(result_urls_list)
            db.commit()

            order.status = OrderStatus.COMPLETED.value
            order.completed_at = datetime.utcnow()
            db.commit()

            styles = _load_styles_data()
            result_labels = _build_result_labels(order, result_urls_list, styles)
            EmailService().send_result_ready(
                order_id, order.email, result_urls_list, order.style_name, result_labels=result_labels
            )

        except StyleTransferRateLimit as e:
            order.status = OrderStatus.FAILED.value
            order.style_transfer_error = f"Rate limit: {e}"
            order.failed_at = datetime.utcnow()
            db.commit()
        except (StyleTransferTimeout, StyleTransferError) as e:
            msg = str(e)
            # Transient upstream source-url failures (catbox/litterbox 504) should be retried.
            if ("504" in msg and "Gateway Time-out" in msg) or ("litter.catbox.moe" in msg):
                logger.warning("Transient source image error for %s, will retry automatically: %s", order_id, msg)
                order.status = OrderStatus.PROCESSING.value
                order.style_transfer_error = msg
                db.commit()
                return
            order.status = OrderStatus.FAILED.value
            order.style_transfer_error = msg
            order.failed_at = datetime.utcnow()
            db.commit()
            EmailService().send_order_failed(order_id, order.email, msg)
        except Exception as e:
            logger.exception(f"Unexpected error processing order {order_id}")
            order.status = OrderStatus.FAILED.value
            order.style_transfer_error = str(e)
            order.failed_at = datetime.utcnow()
            db.commit()
    finally:
        if lock_acquired:
            _release_order_lock_sync(db, order_id)
        db.close()


def _try_acquire_order_lock_sync(db: Session, order_id: str) -> bool:
    """Cross-process lock using PostgreSQL advisory locks."""
    try:
        row = db.execute(
            text("SELECT pg_try_advisory_lock(hashtext(:order_key)) AS locked"),
            {"order_key": order_id},
        ).first()
        return bool(row and row[0])
    except Exception:
        # If advisory locks are unavailable, continue with in-process guard only.
        logger.warning("Could not acquire advisory lock for %s; proceeding without DB lock", order_id)
        return True


def _release_order_lock_sync(db: Session, order_id: str) -> None:
    try:
        db.execute(
            text("SELECT pg_advisory_unlock(hashtext(:order_key))"),
            {"order_key": order_id},
        )
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
    )
