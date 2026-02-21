"""
FastAPI application for AI art style transfer.
"""
import asyncio
import json
import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Optional

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from clients import ReplicateClient, StyleTransferError, StyleTransferRateLimit, StyleTransferTimeout
from config import get_settings, get_upload_dir


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


from database import Order, OrderStatus, get_db, SessionLocal, init_db
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


def get_provider() -> ReplicateClient:
    settings = get_settings()
    return ReplicateClient(
        api_token=settings.replicate_api_token,
        timeout_seconds=settings.api_timeout_seconds,
        polling_timeout_seconds=settings.polling_timeout_seconds,
        polling_interval_seconds=settings.polling_interval_seconds,
    )


def get_service() -> StyleTransferService:
    return StyleTransferService(provider=get_provider())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Artify service starting")
    get_upload_dir().mkdir(parents=True, exist_ok=True)
    _start_db_init_once()
    supervisor_task = asyncio.create_task(_processing_supervisor_loop())
    yield
    supervisor_task.cancel()
    try:
        await supervisor_task
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
    while True:
        _start_db_init_once()
        db = SessionLocal()
        try:
            orders = db.query(Order).filter(
                Order.status.in_([OrderStatus.PAID.value, OrderStatus.PROCESSING.value])
            ).all()
            for o in orders:
                if o.order_id in _ACTIVE_ORDER_TASKS:
                    continue
                target = _target_image_count(o)
                done = _done_image_count(o)
                if target > 0 and done < target:
                    asyncio.create_task(process_order_style_transfer(o.order_id))
        except Exception as e:
            logger.warning("Supervisor loop temporary DB/error: %s", e)
        finally:
            db.close()
        await asyncio.sleep(20)


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
        image_url = _upload_to_litterbox(str(file_path), f"photo{ext}")
    else:
        image_url = _upload_to_litterbox(str(file_path), f"photo{ext}")

    return JSONResponse({"image_url": image_url})


# ── Styles data helper ───────────────────────────────────────

# Masters pack: one style, 15 reference images (user gets photo in all 15)
STYLE_ID_MASTERS_PACK = 13
MASTERS_PACK_PATHS = [
    f"/static/landing/styles/masters/masters-{i:02d}.jpg" for i in range(1, 16)
]


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

    order_id = f"ART-{int(datetime.utcnow().timestamp() * 1000)}-{uuid.uuid4().hex[:8].upper()}"

    style_image_url = _resolve_style_image_url(style_data.get("styleImageUrl") if style_data else None)
    style_image_urls = None
    if order_data.style_id == STYLE_ID_MASTERS_PACK:
        style_image_urls = json.dumps([_resolve_style_image_url(p) for p in MASTERS_PACK_PATHS])
        if not style_image_url:
            style_image_url = _resolve_style_image_url(MASTERS_PACK_PATHS[0])

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

    order = Order(
        order_id=order_id,
        status=OrderStatus.PENDING.value,
        email=order_data.email,
        style_id=order_data.style_id,
        style_name=style_data.get("title") if style_data else None,
        image_url=order_data.image_url,
        style_image_url=style_image_url,
        style_image_urls=style_image_urls,
        amount=12.00,
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
    return OrderStatusResponse(
        order_id=order.order_id,
        status=order.status,
        result_urls=order.result_urls,
        replicate_prediction_details=order.replicate_prediction_details,
        error=order.style_transfer_error,
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
    try:
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
        if order.status == OrderStatus.PROCESSING.value and order.result_urls:
            try:
                result_urls_list = json.loads(order.result_urls) if isinstance(order.result_urls, str) else (order.result_urls or [])
                job_ids = (order.style_transfer_job_id or "").split(",") if order.style_transfer_job_id else []
                if order.replicate_prediction_details:
                    prediction_details = json.loads(order.replicate_prediction_details) if isinstance(order.replicate_prediction_details, str) else (order.replicate_prediction_details or [])
                if isinstance(result_urls_list, list) and len(result_urls_list) < len(style_urls):
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

            service = get_service()
            remaining_style_urls = style_urls[skip:]
            for i, style_url in enumerate(remaining_style_urls):
                if i > 0:
                    time.sleep(6)
                result_url, job_id = service.transfer_style_sync(
                    image_url=order.image_url,
                    style_image_url=style_url,
                )
                result_urls_list.append(result_url)
                job_ids.append(job_id)
                try:
                    pred = service.provider.get_prediction(job_id)
                    prediction_details.append({
                        "id": pred.get("id"),
                        "status": pred.get("status"),
                        "error": pred.get("error"),
                        "metrics": pred.get("metrics"),
                        "created_at": pred.get("created_at"),
                        "started_at": pred.get("started_at"),
                        "completed_at": pred.get("completed_at"),
                        "result_url": result_url,
                        "model": pred.get("model"),
                        "version": pred.get("version"),
                        "source": pred.get("source"),
                        "data_removed": pred.get("data_removed"),
                        "urls": pred.get("urls"),
                        "logs": (pred.get("logs") or "")[:500] if pred.get("logs") else None,
                    })
                except Exception:
                    prediction_details.append({"id": job_id, "status": "succeeded", "result_url": result_url})

                order.result_urls = json.dumps(result_urls_list)
                order.style_transfer_job_id = ",".join(job_ids)
                order.replicate_prediction_details = json.dumps(prediction_details)
                db.commit()

            order.status = OrderStatus.COMPLETED.value
            order.completed_at = datetime.utcnow()
            db.commit()

            first_result_url = result_urls_list[0] if result_urls_list else None
            EmailService().send_result_ready(order_id, order.email, first_result_url, order.style_name)

        except StyleTransferRateLimit as e:
            order.status = OrderStatus.FAILED.value
            order.style_transfer_error = f"Rate limit: {e}"
            order.failed_at = datetime.utcnow()
            db.commit()
        except (StyleTransferTimeout, StyleTransferError) as e:
            order.status = OrderStatus.FAILED.value
            order.style_transfer_error = str(e)
            order.failed_at = datetime.utcnow()
            db.commit()
            EmailService().send_order_failed(order_id, order.email, str(e))
        except Exception as e:
            logger.exception(f"Unexpected error processing order {order_id}")
            order.status = OrderStatus.FAILED.value
            order.style_transfer_error = str(e)
            order.failed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
    )
