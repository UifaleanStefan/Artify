# Artify – Complete Codebase Reference

This document is the single source of truth for the Artify project. It covers every file, every concept, the full architecture, all data flows, and all conventions. A developer on a fresh machine with no prior context should be able to understand and work on the project after reading this.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Repository Structure](#2-repository-structure)
3. [Environment Setup](#3-environment-setup)
4. [Architecture](#4-architecture)
5. [User Funnel – The 5-Step Flow](#5-user-funnel--the-5-step-flow)
6. [Backend – main.py](#6-backend--mainpy)
7. [Database – database.py](#7-database--databasepy)
8. [Style Packs](#8-style-packs)
9. [Payment Flow – Stripe](#9-payment-flow--stripe)
10. [Image Generation Flow](#10-image-generation-flow)
11. [Email Service](#11-email-service)
12. [Frontend Pages & JavaScript](#12-frontend-pages--javascript)
13. [CSS Architecture](#13-css-architecture)
14. [styles-data.js – The Style Catalog](#14-styles-datajs--the-style-catalog)
15. [State: URL Params & sessionStorage](#15-state-url-params--sessionstorage)
16. [Debug & Admin Tools](#16-debug--admin-tools)
17. [Deployment – Render.com](#17-deployment--rendercom)
18. [Key Conventions & Rules](#18-key-conventions--rules)

---

## 1. Project Overview

**Artify** is an AI-powered portrait generation SaaS targeting the Romanian market. Customers upload a photo, choose an art style pack, pay, and receive 5 or 15 AI-generated portraits styled after famous paintings — delivered by email within minutes.

| Property | Value |
|---|---|
| Language | Python 3.11+ (backend), vanilla JS (frontend) |
| Framework | FastAPI |
| Database | PostgreSQL (via SQLAlchemy ORM) |
| AI providers | OpenAI (`gpt-image-1.5` via `/v1/images/edits`) or Replicate (`fofr/style-transfer`) |
| Payments | Stripe Checkout (hosted) |
| Email | Resend (primary) → SendGrid → SMTP (fallback chain) |
| Hosting | Render.com |
| Currency | RON (Romanian Lei) — displayed as `9,99 Lei` (Romanian decimal comma) |
| UI language | Romanian |

---

## 2. Repository Structure

```
Artify/
│
├── main.py                        # FastAPI app: all routes, business logic, background tasks
├── database.py                    # SQLAlchemy models + DB setup + migrations
├── config.py                      # Pydantic settings loaded from .env
├── requirements.txt               # Python dependencies
├── .env.example                   # Template for required environment variables
├── Procfile                       # Process file (Heroku/Render web dyno)
├── render.yaml                    # Render.com deployment blueprint
├── DEPLOY.md                      # Deployment notes
│
├── models/
│   ├── __init__.py                # Exports StyleTransferResponse
│   ├── schemas.py                 # StyleTransferRequest / StyleTransferResponse Pydantic models
│   └── order_schemas.py           # OrderCreateRequest, OrderResponse, OrderStatusResponse
│
├── services/
│   ├── __init__.py                # Exports StyleTransferService
│   ├── style_transfer.py          # StyleTransferService: wraps OpenAI or Replicate client
│   └── email_service.py           # EmailService: Resend → SendGrid → SMTP priority chain
│
├── clients/
│   ├── __init__.py                # Exports all clients + exception classes
│   ├── openai_stylize_client.py   # OpenAI /v1/images/edits client with retry logic
│   └── replicate_client.py        # Replicate API client with polling + rate limit handling
│
├── scripts/
│   ├── init_db_manual.py          # Run once to create DB tables (used in Render pre-deploy)
│   ├── check_orders.py            # Admin: list/inspect orders in DB
│   ├── check_replicate_predictions.py  # Admin: inspect Replicate prediction history
│   ├── get_last_result_urls.py    # Admin: print last order's result URLs
│   ├── view_order_results.py      # Admin: open result images in browser
│   ├── test_replicate.py          # Manual test for Replicate integration
│   ├── setup_ancient_worlds_pack.py    # One-time setup script for Ancient Worlds pack
│   ├── setup_evolution_portraits_pack.py
│   ├── setup_modern_abstract_pack.py
│   ├── setup_royalty_portraits_pack.py
│   └── setup_masters_pack.py
│
└── static/
    └── landing/
        │
        ├── ── HTML Pages ──
        ├── index.html             # Homepage (/)
        ├── styles.html            # Style gallery (/styles)
        ├── upload.html            # Step 2: Upload photo (/upload)
        ├── details.html           # Step 3: Email entry (/details)
        ├── billing.html           # Step 4: Billing address (/billing)
        ├── payment.html           # Step 5: Order summary + pay (/payment)
        ├── payment_success.html   # Post-Stripe redirect (/payment/success)
        ├── payment_cancel.html    # Stripe cancel redirect (/payment/cancel)
        ├── create_done.html       # Order placed, AI processing (/create/done)
        ├── order_status.html      # Museum gallery for completed orders (/order/{id})
        ├── marketing.html         # Internal demo tool (/marketing)
        ├── help.html              # FAQ / Help center (/help)
        ├── contact.html           # Contact form (/contact)
        ├── terms.html             # Terms & Conditions (/terms)
        ├── privacy.html           # Privacy Policy (/privacy)
        ├── debug_order.html       # Debug: inspect any order (/debug/order)
        └── debug_last_results.html # Debug: last order results (/debug/last-results)
        │
        ├── ── CSS ──
        ├── styles.css             # Global stylesheet (shared by ALL pages)
        ├── styles-gallery.css     # Style gallery grid + cards
        ├── upload.css             # Upload page layout
        ├── details.css            # Details page layout
        ├── billing.css            # Billing form layout
        ├── payment.css            # Payment card layout
        ├── order_status.css       # Museum gallery theme
        ├── create_done.css        # Order confirmation page
        ├── contact.css            # Contact page
        ├── help.css               # Help/FAQ page
        ├── legal.css              # Shared Terms + Privacy layout
        └── debug_order.css        # Debug page
        │
        ├── ── JavaScript ──
        ├── script.js              # Global JS: header, hamburger menu, scroll effects, animations
        ├── styles-data.js         # STYLES_DATA array: all 6 style packs metadata
        ├── styles-gallery.js      # Gallery page: render cards, search, filter
        ├── upload.js              # Upload page: file pick, API upload, redirect
        ├── details.js             # Details page: email form, navigation
        ├── billing.js             # Billing page: address form, sessionStorage
        ├── payment.js             # Payment page: create order + Stripe checkout
        ├── order_status.js        # Order status: polling + museum gallery renderer
        ├── create_done.js         # Confirmation page: polls for completion
        ├── marketing.js           # Internal demo: style transfer
        ├── testimonials.js        # Testimonial infinite scroll (horizontal + vertical)
        ├── style-cards-scroll.js  # Style cards strip infinite scroll
        └── demo-compare.js        # Before/after comparison slider (homepage)
        │
        └── styles/                # Reference painting images (90 total)
            ├── masters/           # masters-01.jpg … masters-15.jpg
            ├── impression-color/  # impression-color-01.jpg … -15.jpg
            ├── modern-abstract/   # modern-abstract-01.jpg … -15.jpg
            ├── ancient-worlds/    # ancient-worlds-01.jpg … -15.jpg
            ├── evolution-portraits/ # evolution-portraits-01.jpg … -15.jpg
            └── royalty-portraits/ # royalty-portraits-01.jpg … -15.jpg
```

---

## 3. Environment Setup

### Step 1 – Clone and install dependencies

```bash
git clone <repo-url>
cd Artify
pip install -r requirements.txt
```

### Step 2 – Create `.env`

```bash
cp .env.example .env
# Then fill in all values
```

### Step 3 – Initialize the database

```bash
python scripts/init_db_manual.py
```

### Step 4 – Run locally

```bash
uvicorn main:app --reload
# App available at http://localhost:8000
```

---

### Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `STYLE_TRANSFER_PROVIDER` | Yes | `openai` (default) or `replicate` |
| `OPENAI_API_KEY` | Yes (if OpenAI) | `sk-...` from platform.openai.com |
| `OPENAI_STYLIZE_BASE_URL` | No | Override API base URL (default: `https://api.openai.com`) |
| `OPENAI_STYLIZE_MODEL` | No | Default: `gpt-image-1.5` |
| `OPENAI_STYLIZE_QUALITY` | No | `low` (~$0.01/img), `medium` (~$0.04), `high` (~$0.17). Default: `low` |
| `REPLICATE_API_TOKEN` | Yes (if Replicate) | `r8_...` from replicate.com. Also used as OpenAI fallback. |
| `DATABASE_URL` | Yes | PostgreSQL connection string: `postgresql://user:pass@host:5432/db` |
| `PUBLIC_BASE_URL` | Yes | Your live HTTPS URL, e.g. `https://artify.onrender.com`. Used to build image URLs in emails and API responses. |
| `RESEND_API_KEY` | Recommended | `re_...` from resend.com. Free tier: 100 emails/day. |
| `SENDGRID_API_KEY` | Optional | Fallback email provider. |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | Optional | SMTP fallback. Port default: 587. |
| `FROM_EMAIL` | No | Sender address. Default: `noreply@artifyai.com` |
| `FROM_NAME` | No | Sender name. Default: `Artify` |
| `STRIPE_SECRET_KEY` | Yes | `sk_live_...` or `sk_test_...` from Stripe dashboard |
| `STRIPE_PUBLISHABLE_KEY` | Yes | `pk_live_...` or `pk_test_...` |
| `STRIPE_WEBHOOK_SECRET` | Yes | `whsec_...` — from Stripe dashboard webhook endpoint |
| `UPLOAD_DIR` | No | Directory for uploaded photos. Default: OS temp dir. Use a persistent path on server. |
| `RESULT_IMAGE_TTL_DAYS` | No | Days before result image blobs are deleted from DB. Default: `14` |

> **Important**: `PUBLIC_BASE_URL` must be set to your actual HTTPS domain. It is used to construct absolute URLs for result images in emails and API responses. Without it, image delivery will fail.

---

## 4. Architecture

```mermaid
flowchart TD
    Browser -->|"GET /page"| FastAPI
    FastAPI -->|"FileResponse HTML"| Browser
    Browser -->|"fetch() API calls"| FastAPI
    FastAPI --> PostgreSQL
    FastAPI --> OpenAI["OpenAI API\n(gpt-image-1.5)"]
    FastAPI --> Replicate["Replicate API\n(fofr/style-transfer)"]
    FastAPI --> Stripe["Stripe Checkout"]
    FastAPI --> EmailSvc["EmailService"]
    Stripe -->|"webhook POST /api/stripe/webhook"| FastAPI
    EmailSvc --> Resend
    EmailSvc --> SendGrid
    EmailSvc --> SMTP
```

### Key architectural decisions

- **No template engine.** All HTML files are pre-built static files served via `FileResponse`. There is no Jinja2, no server-side rendering. State between pages is passed via URL query parameters and `sessionStorage`.
- **Single Python process.** `main.py` handles everything: page serving, API routes, background processing, scheduled tasks.
- **Background tasks run inside the app process.** Two async loops run as `asyncio.Task` objects: a supervisor (every 20s) and a TTL cleanup (every 24h). Individual order processing runs as a `BackgroundTask` in a thread pool.
- **Images stored in PostgreSQL.** Result images are stored as binary blobs in `art_order_result_images` so they survive server redeploys (Render's disk is ephemeral). They are also written to disk as a redundant backup.
- **Static files** are served by Starlette's `StaticFiles` middleware mounted at `/static`.

---

## 5. User Funnel – The 5-Step Flow

```
Homepage (/)
  └─> Style Gallery (/styles)
        └─> Upload Photo (/upload?style=13&pack=5)
              └─> Email Details (/details?style=13&image_url=...&portrait_mode=realistic&pack=5)
                    └─> Billing Address (/billing?style=13&image_url=...&portrait_mode=...&pack=5&email=...)
                          └─> Order Summary (/payment?style=13&image_url=...&portrait_mode=...&pack=5&email=...)
                                └─> [POST /api/orders] → creates DB record (status=pending)
                                └─> [POST /api/orders/{id}/checkout] → creates Stripe session
                                └─> Stripe Checkout (external, hosted by Stripe)
                                      ├─> /payment/success?order_id=ART-xxx  (user paid)
                                      └─> /payment/cancel?order_id=ART-xxx   (user cancelled)
                                            └─> /create/done?order_id=...&style=...&email=...
                                                  └─> [Stripe webhook] → status=paid → AI processing starts
                                                        └─> Email sent with gallery link
                                                              └─> /order/ART-xxx  (museum gallery)
```

### URL parameters passed through the funnel

| Param | Type | Description |
|---|---|---|
| `style` | integer | Style pack ID (13–18) |
| `pack` | integer | Number of portraits: `5` or `15` |
| `image_url` | string | Absolute URL of uploaded photo (from `/api/upload-image`) |
| `portrait_mode` | string | `realistic` or `artistic` |
| `email` | string | Customer's delivery email |
| `order_id` | string | Order ID like `ART-1700000000000-ABCD1234` |

### sessionStorage key

| Key | Set by | Read by | Contents |
|---|---|---|---|
| `billingInfo` | `billing.js` | `payment.js` | JSON object: `{fullName, address1, address2, city, state, zip, country}` |

---

## 6. Backend – main.py

`main.py` is the entire backend in one file (~1974 lines). It is a FastAPI application.

### Startup sequence (`lifespan`)

1. Logs the active style transfer provider
2. Calls `get_upload_dir().mkdir()` to ensure upload directory exists
3. Calls `_start_db_init_once()` — runs `init_db()` in a background thread
4. Starts `_processing_supervisor_loop()` as an asyncio task
5. Starts `_ttl_cleanup_loop()` as an asyncio task

### Middleware

- `SecurityHeadersMiddleware`: adds `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy` to all responses.
- Global exception handler: catches unhandled exceptions, logs them, returns `{"detail": "A server error occurred."}` (never leaks stack traces to clients).

### Page Routes (all return `FileResponse` with `no-cache` headers)

| Method | Path | HTML File |
|---|---|---|
| GET | `/` | `index.html` |
| GET | `/styles` | `styles.html` |
| GET | `/upload` | `upload.html` |
| GET | `/details` | `details.html` |
| GET | `/billing` | `billing.html` |
| GET | `/payment` | `payment.html` |
| GET | `/payment/success` | `payment_success.html` |
| GET | `/payment/cancel` | `payment_cancel.html` |
| GET | `/create/done` | `create_done.html` |
| GET | `/help` | `help.html` |
| GET | `/contact` | `contact.html` |
| GET | `/terms` | `terms.html` |
| GET | `/privacy` | `privacy.html` |
| GET | `/marketing` | `marketing.html` |
| GET | `/order/{order_id}` | `order_status.html` |
| GET | `/debug/order` | `debug_order.html` |
| GET | `/debug/last-results` | `debug_last_results.html` |

### API Routes

#### Upload

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/upload-image` | Accepts multipart `file` upload. Saves to disk + DB (`art_order_source_images`). Returns `{"image_url": "..."}` |
| GET | `/api/uploads/{upload_id}/{filename}` | Serves an uploaded photo. Tries disk first, falls back to DB. |

#### Orders

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/orders` | Creates a new order. Body: `OrderCreateRequest`. Returns `OrderResponse`. |
| GET | `/api/orders/{order_id}` | Returns full order data as `OrderResponse`. |
| GET | `/api/orders/{order_id}/status` | Returns `OrderStatusResponse` with status, result URLs, labels. Used for polling. |
| GET | `/api/orders/{order_id}/result/{index}` | Serves a single result image (1-based index). DB first, disk fallback. |
| GET | `/api/orders/{order_id}/source-image` | Serves the customer's uploaded photo. |
| GET | `/api/orders/{order_id}/download-all` | Streams a ZIP archive of all result images. |
| POST | `/api/orders/{order_id}/checkout` | Creates a Stripe Checkout Session. Returns `{"checkout_url": "..."}`. |
| POST | `/api/orders/{order_id}/pay` | Legacy manual payment endpoint (admin/internal only). |

#### Stripe Webhook

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/stripe/webhook` | Receives Stripe events. Verifies signature. On `checkout.session.completed`: sets order `status=paid`, triggers `process_order_style_transfer` as background task. |

#### Marketing / Demo

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/marketing/styles` | Returns all 90 paintings (6 packs × 15) as JSON for the marketing tool. |
| POST | `/api/marketing/style-transfer` | Single high-quality style transfer. Multipart: `image` + `style_id` + `style_index`. Returns image bytes directly. |

#### Debug

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/debug/last-order` | Status of the most recent order. |
| GET | `/api/debug/last-order-results` | Result URLs of the most recent order with results. |
| GET | `/api/debug/last-order-results.txt` | Same, plain text one-per-line. |
| POST | `/api/debug/resume-order/{order_id}` | Re-queues a stuck `processing` order. |
| POST | `/api/debug/resend-ready-email/{order_id}` | Resends the completion email for a `completed` order. |

#### Health

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Returns `{"status": "ok"}`. Used by Render uptime checks. |

---

### Key Functions in main.py

#### `process_order_style_transfer(order_id)`
Async wrapper. Adds `order_id` to `_ACTIVE_ORDER_TASKS` set, runs `_run_style_transfer_sync` in a thread pool, removes from set when done.

#### `_run_style_transfer_sync(order_id)`
The core order processing function. Runs synchronously in a thread:

1. Acquires a PostgreSQL advisory lock (`pg_try_advisory_lock`) — prevents duplicate processing if supervisor re-queues an already-running order.
2. Loads the order from DB. Validates it is `paid` or `processing`.
3. Sets status to `processing`.
4. Determines the list of style image URLs from `order.style_image_urls` (JSON array).
5. Checks how many results already exist (crash recovery — resumes from where it left off).
6. For each remaining style image URL:
   - Calls `_style_url_to_prompt(url)` to get the detailed text prompt for that painting.
   - Calls `service.transfer_style_sync(image_url, style_image_url, prompt, portrait_mode)`.
   - On OpenAI failure (3 attempts): falls back to Replicate if `REPLICATE_API_TOKEN` is set.
   - Waits 30 seconds between requests (rate limiting).
7. Calls `_persist_result_images(order_id, result_items)` to save all results to DB + disk.
8. Sets `order.result_urls` to the permanent URL list, `status=completed`, `completed_at=now`.
9. Calls `EmailService().send_result_ready(...)`.

#### `_style_url_to_prompt(style_image_url)`
Parses the filename from a style image URL (e.g. `masters-02.jpg` → index 2 → `MASTERS_PACK_PROMPTS[1]`). Returns the detailed OpenAI text prompt for that specific painting. Each pack has its own `PACK_PROMPTS` array in `main.py`.

#### `_persist_result_images(order_id, result_items)`
For each result (either bytes dict from OpenAI or URL string from Replicate):
- Stores binary in `art_order_result_images` table (keyed by `order_id` + `image_index`).
- Writes to disk at `artify_order_results/{order_id}/{i}.jpg`.
- Returns list of permanent URLs: `/api/orders/{order_id}/result/{i}`.

#### `_processing_supervisor_loop()`
Runs every 20 seconds. Queries DB for all orders with `status IN ('paid', 'processing')`. For each that is not already in `_ACTIVE_ORDER_TASKS`, creates a new asyncio task to process it. This self-heals orders that were interrupted by a server restart.

#### `_ttl_cleanup_loop()`
Runs every 24 hours. Deletes `art_order_result_images` rows older than `RESULT_IMAGE_TTL_DAYS` (default 14). Keeps source images and order records.

#### `_resolve_style_image_url(url)`
Converts relative paths (e.g. `/static/landing/styles/masters/masters-01.jpg`) to absolute HTTPS URLs using `PUBLIC_BASE_URL`. Required because OpenAI and Replicate APIs need publicly accessible URLs.

#### `_build_result_labels(order, urls, styles)`
Returns a list of `(painting_title, artist_name)` tuples for each result image, used in the email body.

#### `get_provider()`
Factory function. Returns `OpenAIStylizeClient` or `ReplicateClient` based on `STYLE_TRANSFER_PROVIDER` env var.

#### `get_replicate_service()`
Returns a `StyleTransferService` wrapping Replicate, used as fallback when OpenAI fails. Returns `None` if `REPLICATE_API_TOKEN` is not set.

---

## 7. Database – database.py

PostgreSQL database accessed via SQLAlchemy ORM. Three tables.

### Connection

`get_database_url()` reads `DATABASE_URL` from env (or `POSTGRES_URL` as fallback). Automatically converts `postgres://` → `postgresql://` (Render uses the old prefix).

Connection pool: `pool_size=5`, `max_overflow=10`, `connect_timeout=10s`, `pool_pre_ping=True`.

### `OrderStatus` enum

```
pending → paid → processing → completed
                            → failed
                            → cancelled
```

### Table: `art_orders`

| Column | Type | Description |
|---|---|---|
| `id` | Integer PK | Auto-increment internal ID |
| `order_id` | String(50) | Public ID: `ART-{timestamp}-{random8}` |
| `status` | String(20) | `OrderStatus` enum value |
| `email` | String(255) | Customer delivery email |
| `style_id` | Integer | Style pack ID (13–18) |
| `style_name` | String(255) | Human-readable pack name |
| `image_url` | Text | URL of customer's uploaded photo |
| `portrait_mode` | String(20) | `realistic` or `artistic` |
| `style_image_url` | Text | Primary style reference image URL |
| `style_image_urls` | Text | JSON array of all style reference URLs (5 or 15 items) |
| `result_urls` | Text | JSON array of permanent result image URLs |
| `style_transfer_job_id` | Text | Comma-separated job IDs (Replicate prediction IDs) |
| `style_transfer_error` | Text | Error message if processing failed |
| `replicate_prediction_details` | Text | JSON array of full Replicate prediction objects |
| `amount` | Float | Order amount: `9.99` or `19.99` |
| `payment_status` | String(20) | `pending`, `paid`, etc. |
| `payment_provider` | String(50) | `stripe` |
| `payment_transaction_id` | String(255) | Stripe session ID |
| `created_at` | DateTime | UTC timestamp |
| `paid_at` | DateTime | When Stripe webhook confirmed payment |
| `completed_at` | DateTime | When all images were generated |
| `failed_at` | DateTime | When processing failed |
| `billing_name` | String(255) | Full name from billing form |
| `billing_address` | Text | Street address |
| `billing_city` | String(100) | City |
| `billing_state` | String(100) | County/state |
| `billing_zip` | String(20) | Postal code |
| `billing_country` | String(100) | Country |

### Table: `art_order_result_images`

Stores generated portrait images as binary blobs. Composite primary key: `(order_id, image_index)`.

| Column | Type | Description |
|---|---|---|
| `order_id` | String(50) PK | References order |
| `image_index` | Integer PK | 1-based index (1 to 15) |
| `content_type` | String(32) | `image/jpeg`, `image/png`, or `image/webp` |
| `data` | LargeBinary | Raw image bytes |
| `created_at` | DateTime | Used for 14-day TTL cleanup |

### Table: `art_order_source_images`

Stores the customer's uploaded photo. Survives server redeploys (Render's disk is ephemeral).

| Column | Type | Description |
|---|---|---|
| `order_id` | String(50) PK | References order |
| `content_type` | String(32) | MIME type |
| `data` | LargeBinary | Raw photo bytes |
| `created_at` | DateTime | Upload timestamp |

### `init_db()`

Creates all tables via `Base.metadata.create_all()`. Also runs `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` migrations for columns added after initial deploy (`portrait_mode`, `style_image_urls`, `replicate_prediction_details`). Safe to run multiple times.

---

## 8. Style Packs

### Overview

There are 6 style packs. Each pack contains 15 reference paintings stored as JPG/PNG files in `static/landing/styles/`. The pack ID is an integer used throughout the frontend and backend.

| ID | Pack Name | Folder | Status |
|---|---|---|---|
| 13 | Tu, pictat de maeștri (Masters) | `masters/` | Active |
| 14 | Impresie și culoare (Impressionism) | `impression-color/` | Active |
| 15 | Modern și abstract | `modern-abstract/` | Active |
| 16 | Lumi antice (Ancient Worlds) | `ancient-worlds/` | Coming Soon |
| 17 | Evoluția portretelor | `evolution-portraits/` | Coming Soon |
| 18 | Portrete regale și imperiale | `royalty-portraits/` | Coming Soon |

### Pack Tiers (Pricing)

| Tier | Portraits | Price |
|---|---|---|
| 5-portrait | 5 paintings from the pack | 9,99 Lei |
| 15-portrait | All 15 paintings from the pack | 19,99 Lei |

The `pack` URL parameter (`5` or `15`) controls how many style images are included in `style_image_urls` when the order is created.

### How packs are defined in main.py

For each pack, `main.py` defines three parallel arrays:

```python
MASTERS_PACK_PATHS = [
    "/static/landing/styles/masters/masters-01.jpg",
    "/static/landing/styles/masters/masters-02.jpg",
    # ... 15 entries
]

MASTERS_PACK_LABELS = [
    ("Portrait of a Man", "Jan van Eyck"),
    ("Self-Portrait", "Rembrandt van Rijn"),
    # ... 15 entries — (painting_title, artist_name)
]

MASTERS_PACK_PROMPTS = [
    "Transform this portrait in the style of Jan van Eyck's Flemish oil painting technique...",
    "Apply Rembrandt's chiaroscuro technique...",
    # ... 15 detailed text prompts for OpenAI
]
```

The index in these arrays corresponds to the painting number in the filename (1-based). For example, `masters-02.jpg` → index 1 (0-based) → `MASTERS_PACK_LABELS[1]` → `MASTERS_PACK_PROMPTS[1]`.

### `_style_url_to_prompt(style_image_url)`

This function is critical for OpenAI generation. It:
1. Extracts the filename from the URL (e.g. `masters-02.jpg`).
2. Identifies the pack by the filename prefix (`masters`, `impression-color`, etc.).
3. Parses the number from the filename (`02` → index `1` in 0-based array).
4. Returns the corresponding prompt from the pack's `PACK_PROMPTS` array.
5. If `portrait_mode == "artistic"`, appends a longer painterly suffix to the prompt.

> **Critical**: The filenames in `static/landing/styles/` must stay in sync with the array indices in `main.py`. If you add or reorder paintings, update both.

---

## 9. Payment Flow – Stripe

### Flow diagram

```mermaid
sequenceDiagram
    participant Browser
    participant FastAPI
    participant Stripe
    participant DB

    Browser->>FastAPI: POST /api/orders (OrderCreateRequest)
    FastAPI->>DB: INSERT order (status=pending)
    FastAPI-->>Browser: {order_id: "ART-xxx"}

    Browser->>FastAPI: POST /api/orders/ART-xxx/checkout
    FastAPI->>Stripe: stripe.checkout.Session.create(...)
    Stripe-->>FastAPI: {url: "https://checkout.stripe.com/..."}
    FastAPI-->>Browser: {checkout_url: "..."}

    Browser->>Stripe: redirect to checkout URL
    Note over Browser,Stripe: Customer enters card details

    Stripe->>Browser: redirect to /payment/success?order_id=ART-xxx
    Stripe->>FastAPI: POST /api/stripe/webhook (checkout.session.completed)
    FastAPI->>FastAPI: verify signature with STRIPE_WEBHOOK_SECRET
    FastAPI->>DB: UPDATE order SET status=paid, paid_at=now
    FastAPI->>FastAPI: background_tasks.add_task(process_order_style_transfer, order_id)
```

### Stripe Checkout Session parameters

- `mode`: `payment`
- `currency`: `ron`
- `line_items`: one item with the pack name and price (9.99 or 19.99 Lei)
- `metadata`: `{"order_id": "ART-xxx"}` — used to match the webhook event to the DB order
- `success_url`: `{PUBLIC_BASE_URL}/payment/success?order_id=ART-xxx`
- `cancel_url`: `{PUBLIC_BASE_URL}/payment/cancel?order_id=ART-xxx`

### Webhook verification

The webhook handler reads the raw request body and verifies the `Stripe-Signature` header using `stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)`. If verification fails, returns HTTP 400. Never process unverified webhook events.

### Stripe dashboard setup

1. Create a webhook endpoint pointing to `https://{your-domain}/api/stripe/webhook`.
2. Subscribe to event: `checkout.session.completed`.
3. Copy the webhook signing secret (`whsec_...`) to `STRIPE_WEBHOOK_SECRET` env var.

---

## 10. Image Generation Flow

### Provider selection

Set `STYLE_TRANSFER_PROVIDER` in `.env`:
- `openai` (default): uses `gpt-image-1.5` via `/v1/images/edits`
- `replicate`: uses `fofr/style-transfer` model on Replicate

### OpenAI provider (`clients/openai_stylize_client.py`)

- Endpoint: `POST {OPENAI_STYLIZE_BASE_URL}/v1/images/edits`
- Model: `gpt-image-1.5` (or `gpt-image-1-mini` for cheaper)
- Quality: `low` / `medium` / `high` (controls cost and quality)
- Payload: `images=[{image_url}]`, `prompt` (detailed text), `n=1`, `size=1024x1024`, `moderation=low`
- Response: decodes `b64_json` field → returns `(bytes, content_type)`. Falls back to fetching `url` field if no b64.
- Retry logic: up to 8 attempts with exponential backoff on 429 (rate limit) and 5xx errors.

### Replicate provider (`clients/replicate_client.py`)

- Model: `fofr/style-transfer:f1023890703bc0a5a3a2c21b5e498833be5f6ef6e70e9daf6b9b3a4fd8309cf0`
- Inputs: `structure_image` (user photo URL), `style_image` (reference painting URL), `prompt` (preserve face identity), `negative_prompt`, `output_format=jpg`
- Flow: `submit_style_transfer()` → returns prediction ID → `poll_result()` polls every 5s up to 600s → returns output URL when `status=succeeded`
- Exception classes: `StyleTransferError`, `StyleTransferRateLimit`, `StyleTransferTimeout`

### Fallback logic

If `STYLE_TRANSFER_PROVIDER=openai` and OpenAI fails 3 consecutive times on a single image, the system automatically falls back to Replicate (if `REPLICATE_API_TOKEN` is set). The fallback is per-image, not per-order.

### Portrait modes

| Mode | Effect |
|---|---|
| `realistic` | Standard prompt — preserves facial features more closely |
| `artistic` | Appends a longer painterly suffix to the prompt — more stylized, less face-accurate |

### Rate limiting

A 30-second delay is inserted between each style transfer request within an order. This prevents hitting API rate limits when processing 15 images sequentially.

### Result persistence

After each image is generated:
1. Stored as binary in `art_order_result_images` table (survives redeploys).
2. Written to disk at `{UPLOAD_DIR}/../artify_order_results/{order_id}/{i}.jpg`.
3. Permanent URL set to `/api/orders/{order_id}/result/{i}`.

The `/api/orders/{order_id}/result/{i}` endpoint serves from DB first, falls back to disk.

---

## 11. Email Service

**File**: `services/email_service.py`

### Provider priority chain

```
Resend (RESEND_API_KEY set?) → SendGrid (SENDGRID_API_KEY set?) → SMTP (SMTP_HOST set?)
```

The first configured provider is used. If all fail, the error is logged but does not crash the order.

### Emails sent

#### Completion email (`send_result_ready`)
- **Subject**: `Galeria ta e gata — descoperă portretele!` (Romanian)
- **Content**: HTML email with gallery link (`/order/{order_id}`) and ZIP download link (`/api/orders/{order_id}/download-all`)
- **Includes**: painting title and artist name for each portrait

#### Failure email (`send_order_failed`)
- Sent if processing fails after all retries
- Contains order ID and error summary

### SMTP retry logic

3 attempts with exponential backoff. Tries TLS first, falls back to plain SMTP.

---

## 12. Frontend Pages & JavaScript

### Global conventions for every HTML page

Every HTML page must follow this structure:

```html
<body>
  <!-- 1. Promo banner FIRST -->
  <div class="promo-banner" aria-live="polite">
    <!-- marquee content -->
  </div>

  <!-- 2. Header SECOND -->
  <header class="header header-scroll-fade" id="main-header">
    <a href="/" class="logo">...</a>
    <button type="button" class="hamburger-btn" id="hamburger-btn" ...>...</button>
    <nav class="nav">...</nav>
  </header>

  <!-- 3. Main content -->
  <main class="page-main">
    ...
  </main>

  <!-- 4. Footer -->
  <footer class="footer">...</footer>

  <!-- 5. Mobile menu overlay -->
  <div class="menu-overlay" id="menu-overlay">...</div>

  <!-- 6. script.js MUST be loaded on every page -->
  <script src="/static/landing/script.js" defer></script>
  <!-- page-specific scripts after -->
</body>
```

> **Critical**: `script.js` must be loaded on every page. It initializes the hamburger menu, header scroll effect, and other global behaviors. Without it, the mobile menu will not work.

---

### Page Reference

#### `index.html` — Homepage (`/`)
- **CSS**: `styles.css`
- **JS**: `script.js`, `testimonials.js`, `style-cards-scroll.js`, `demo-compare.js`
- **Sections**: promo banner, header, hero, how-it-works, demo comparison slider, style cards strip, testimonials, pricing cards, FAQ, footer
- **Body class**: `page-home` (applies hero gradient to `body` background for header fade effect)

#### `styles.html` — Style Gallery (`/styles`)
- **CSS**: `styles.css`, `styles-gallery.css`
- **JS**: `styles-data.js`, `styles-gallery.js`, `script.js`
- **`styles-gallery.js`**: reads `STYLES_DATA`, renders cards grid, search by title/artist/description, category filter buttons. Clicking a card links to `/upload?style={id}&pack=5`.

#### `upload.html` — Upload Photo (`/upload`)
- **CSS**: `styles.css`, `upload.css`
- **JS**: `styles-data.js`, `upload.js`, `script.js`
- **URL params read**: `style` (pack ID), `pack` (5 or 15)
- **`upload.js`**: shows selected style card with scrollable preview images; drag-and-drop + file input; on "Continuă": `POST /api/upload-image` → redirects to `/details?style=...&image_url=...&portrait_mode=...&pack=...`

#### `details.html` — Email Entry (`/details`)
- **CSS**: `styles.css`, `details.css`
- **JS**: `script.js`, `styles-data.js`, `details.js`
- **URL params read**: `style`, `image_url`, `portrait_mode`, `pack`
- **`details.js`**: shows style thumbnail and uploaded photo preview; email + confirm email form; on submit: validates match → redirects to `/billing?...`

#### `billing.html` — Billing Address (`/billing`)
- **CSS**: `styles.css`, `billing.css`
- **JS**: `styles-data.js`, `billing.js`, `script.js`
- **URL params read**: `style`, `image_url`, `portrait_mode`, `pack`, `email`
- **`billing.js`**: address form; on submit: saves `billingInfo` to `sessionStorage` → redirects to `/payment?...`

#### `payment.html` — Order Summary & Pay (`/payment`)
- **CSS**: `styles.css`, `payment.css`
- **JS**: `script.js`, `styles-data.js`, `payment.js`
- **URL params read**: `style`, `image_url`, `portrait_mode`, `pack`, `email`
- **sessionStorage read**: `billingInfo`
- **`payment.js`**: shows order summary with price; on "Plătește": `POST /api/orders` → `POST /api/orders/{id}/checkout` → `window.location.href = checkoutUrl` (Stripe redirect)

#### `payment_success.html` — Post-Stripe Success (`/payment/success`)
- **CSS**: `styles.css`, `create_done.css`
- **JS**: `script.js`, inline script
- **URL params read**: `order_id`
- **Inline JS**: polls `GET /api/orders/{order_id}` every 3s up to 60s; on `status=paid/processing/completed` → redirects to `/create/done?order_id=...`

#### `payment_cancel.html` — Payment Cancelled (`/payment/cancel`)
- **CSS**: `styles.css`, `create_done.css`
- **JS**: `script.js`, inline script
- Shows cancellation message with "Încearcă din nou" button linking back to `/styles`

#### `create_done.html` — Order Placed (`/create/done`)
- **CSS**: `styles.css`, `create_done.css`
- **JS**: `script.js`, `styles-data.js`, `create_done.js`
- **URL params read**: `order_id`, `style`, `email`
- **`create_done.js`**: shows order ID, style name, email; polls `GET /api/orders/{id}/status` every 8s up to 10 min; on completion: updates UI to "Galeria ta e gata!"

#### `order_status.html` — Museum Gallery (`/order/{id}`)
- **CSS**: `styles.css`, `order_status.css`
- **JS**: `script.js`, `order_status.js`
- **URL path**: order ID extracted from `window.location.pathname`
- **`order_status.js`**: calls `GET /api/orders/{id}/status`; renders loading/processing/failed/completed states; completed state shows museum gallery: hero image, filmstrip thumbnails, prev/next arrows, before/after compare slider (style painting vs. result), painting title/artist captions, share button (Web Share API), ZIP download link

#### `marketing.html` — Internal Demo (`/marketing`)
- **CSS**: inline styles
- **JS**: `marketing.js`
- **`marketing.js`**: loads all 90 paintings via `GET /api/marketing/styles`; grouped `<optgroup>` selector; on submit: `POST /api/marketing/style-transfer` (multipart: image + style_id + style_index) → displays result image

#### `help.html` — Help Center (`/help`)
- **CSS**: `styles.css`, `help.css`
- **JS**: `script.js`
- Static FAQ content in Romanian

#### `contact.html` — Contact (`/contact`)
- **CSS**: `styles.css`, `contact.css`
- **JS**: `script.js`
- Contact form (currently static display — no backend form handler)

#### `terms.html` — Terms & Conditions (`/terms`)
- **CSS**: `styles.css`, `legal.css`
- **JS**: `script.js`

#### `privacy.html` — Privacy Policy (`/privacy`)
- **CSS**: `styles.css`, `legal.css`
- **JS**: `script.js`

---

### JavaScript File Reference

#### `script.js` — Global (loaded on every page)
- Smooth scroll for `#anchor` links
- Header scroll effect: adds `header-scrolled` class at 40px scroll (makes header opaque)
- Hamburger menu: opens/closes `.menu-overlay` panel, toggles `aria-expanded`
- "How it works" step flash animation on mobile tap
- Demo compare slider auto-sweep on mobile (IntersectionObserver triggers once when card enters viewport)
- Scroll nudge for `.style-cards-track` and `.testimonial-track-h` on mobile (one-time nudge when element enters viewport)

#### `styles-data.js` — Style Catalog
Defines `window.STYLES_DATA` — see [Section 14](#14-styles-datajs--the-style-catalog).

#### `testimonials.js`
- Clones testimonial cards for seamless horizontal infinite scroll
- Also populates two vertical columns for mobile treadmill
- Auto-scrolls at 1px/18ms; pauses on hover/touch

#### `style-cards-scroll.js`
- Clones style cards for seamless horizontal infinite scroll strip on homepage
- Auto-scrolls at 1.5px/16ms; pauses on hover

#### `demo-compare.js`
- Before/after comparison slider for homepage demo cards
- Supports: mouse drag, click-to-jump, touch drag on handle, tap-to-jump

---

## 13. CSS Architecture

### `styles.css` — Global Stylesheet

Loaded on every page. Contains:

**CSS Variables (`:root`)**

| Variable | Value | Purpose |
|---|---|---|
| `--primary` | `#2563eb` | Blue — primary brand color, buttons |
| `--primary-dark` | `#1d4ed8` | Darker blue for hover states |
| `--accent` | `#f59e0b` | Amber — accent/highlight color |
| `--bg` | `#0f172a` | Dark navy — page background |
| `--surface` | `#1e293b` | Slightly lighter surface (cards) |
| `--surface-2` | `#334155` | Even lighter surface (inputs, borders) |
| `--text` | `#f1f5f9` | Near-white — primary text |
| `--text-muted` | `#94a3b8` | Muted gray — secondary text |
| `--font` | `'DM Sans', sans-serif` | Primary font |
| `--radius` | `0.5rem` | Default border radius |
| `--radius-lg` | `1rem` | Large border radius |
| `--radius-xl` | `1.5rem` | Extra large border radius |
| `--shadow` | `0 1px 3px rgba(0,0,0,0.3)` | Subtle shadow |
| `--shadow-lg` | `0 10px 25px rgba(0,0,0,0.4)` | Large shadow |

**Global components styled in `styles.css`:**
- CSS reset and base typography
- `.promo-banner` — sticky top marquee bar
- `.header`, `.header-scroll-fade`, `.header-scrolled` — fixed header with scroll fade
- `.nav`, `.hamburger-btn`, `.hamburger-line` — desktop nav + mobile hamburger
- `.menu-overlay`, `.menu-panel` — mobile slide-in menu
- `.logo`, `.logo-icon`, `.logo-text`
- `.btn`, `.btn-primary`, `.btn-outline`, `.btn-lg`, `.btn-header`
- `.steps-bar`, `.step`, `.step-connector` — funnel progress indicator
- `.hero-*` — homepage hero section
- `.how-it-works-*` — how it works section
- `.demo-compare-*` — before/after slider cards
- `.style-cards-*` — style cards infinite scroll strip
- `.testimonial-*` — testimonials section
- `.pricing-card-*` (`.pc-*`) — pricing cards
- `.footer`, `.footer-grid`, `.footer-col` — site footer
- `body.page-home` — applies hero radial gradient to body background

**Header fade effect**: On `body.page-home`, the body background has the same radial gradient as the hero section. The header starts fully transparent (`background: transparent`). On scroll past 40px, JS adds `.header-scrolled` which sets `background: var(--surface)`. This creates a seamless fade-into-background effect at the top of the homepage.

### Page-specific CSS files

| File | Key classes |
|---|---|
| `styles-gallery.css` | `.styles-main`, `.styles-toolbar`, `.styles-grid`, `.gallery-card`, `.gallery-card-thumb`, `.gallery-tag`, `.coming-soon-overlay` |
| `upload.css` | `.upload-main`, `.upload-grid`, `.upload-left`, `.upload-right`, `.upload-zone`, `.upload-zone-inner`, `.upload-zone-preview`, `.upload-portrait-mode`, `.upload-actions` |
| `details.css` | `.details-main`, `.details-grid`, `.details-left`, `.details-right`, `.details-style-card`, `.details-style-thumb` |
| `billing.css` | `.billing-main`, `.billing-grid`, `.billing-left`, `.billing-right`, `.billing-summary`, `.billing-thumb-wrap` |
| `payment.css` | `.payment-main`, `.payment-card-wrap`, `.payment-card`, `.payment-cost`, `.payment-total` |
| `order_status.css` | `.order-status-main`, `.museum-header`, `.museum-hero`, `.museum-filmstrip`, `.exhibition-arrow`, `.museum-actions` |
| `create_done.css` | `.done-main`, `.done-card`, `.done-title`, `.done-details`, `.done-email-callout` |
| `legal.css` | `.legal-hero`, `.legal-page`, `.legal-toc`, `.legal-section` |

---

## 14. styles-data.js – The Style Catalog

**File**: `static/landing/styles-data.js`

Defines `window.STYLES_DATA` — a global array of 6 style objects. This is the single source of truth for style metadata on the frontend.

### Style object structure

```javascript
{
  "id": 13,                          // Integer ID — must match main.py pack constants
  "title": "Tu, pictat de maeștri",  // Display name (Romanian)
  "artist": "Maeștrii",              // Artist/category label
  "category": "Masters",             // Filter category
  "description": "...",              // Short description
  "rating": 4.9,                     // Star rating displayed on card
  "thumbnailClass": "style-masters-placeholder",  // CSS class (legacy)
  "styleImageUrl": "/static/landing/styles/masters/masters-02.jpg",  // Primary preview image
  "preview": true,                   // Whether preview images are available
  "previewImageUrls": [              // Up to 5 images shown in scrollable preview
    "/static/landing/styles/masters/masters-02.jpg",
    "/static/landing/styles/masters/masters-04.jpg",
    // ...
  ],
  "comingSoon": true                 // Optional — if true, card shows "În curând" overlay
}
```

### How IDs must stay in sync

The `id` field in `STYLES_DATA` must match the constants in `main.py`:

| `STYLES_DATA` id | `main.py` constant |
|---|---|
| 13 | `STYLE_ID_MASTERS_PACK = 13` |
| 14 | `STYLE_ID_IMPRESSION_COLOR_PACK = 14` |
| 15 | `STYLE_ID_MODERN_ABSTRACT_PACK = 15` |
| 16 | `STYLE_ID_ANCIENT_WORLDS_PACK = 16` |
| 17 | `STYLE_ID_EVOLUTION_PORTRAITS_PACK = 17` |
| 18 | `STYLE_ID_ROYALTY_PORTRAITS_PACK = 18` |

> **Warning**: If you add a new style pack, you must: (1) add it to `STYLES_DATA` in `styles-data.js`, (2) add the corresponding constant and three arrays (`PACK_PATHS`, `PACK_LABELS`, `PACK_PROMPTS`) in `main.py`, (3) add the image files to `static/landing/styles/`, (4) update `_style_url_to_prompt()` to handle the new pack's filename prefix.

---

## 15. State: URL Params & sessionStorage

The funnel has no server-side session. All state is passed via URL query parameters between pages, with one exception (billing info in sessionStorage).

### URL parameters

| Param | Pages | Description |
|---|---|---|
| `style` | upload → details → billing → payment | Style pack ID (integer, e.g. `13`) |
| `pack` | upload → details → billing → payment | Number of portraits: `5` or `15` |
| `image_url` | upload → details → billing → payment | Absolute URL of uploaded photo |
| `portrait_mode` | upload → details → billing → payment | `realistic` or `artistic` |
| `email` | details → billing → payment | Customer email address |
| `order_id` | payment/success → create/done → order status | Order ID string (`ART-xxx`) |

### sessionStorage

| Key | Set by | Read by | Shape |
|---|---|---|---|
| `billingInfo` | `billing.js` on form submit | `payment.js` on page load | `{fullName, address1, address2, city, state, zip, country}` |

> **Note**: sessionStorage is cleared when the browser tab is closed. If a user opens the payment page in a new tab, billing info will be missing. This is a known limitation.

---

## 16. Debug & Admin Tools

### Web-based debug pages

| URL | Purpose |
|---|---|
| `/debug/order` | Enter any order ID → shows all result images + raw Replicate prediction JSON |
| `/debug/last-results` | Shows result images from the most recent order that has results |

### Debug API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/debug/last-order` | JSON status of the most recent order |
| `GET /api/debug/last-order-results` | JSON with result URLs of the most recent order with results |
| `GET /api/debug/last-order-results.txt` | Plain text URL list (one per line) |
| `POST /api/debug/resume-order/{order_id}` | Re-queues a stuck `processing` order. Use when a server restart interrupted processing. |
| `POST /api/debug/resend-ready-email/{order_id}` | Resends the completion email for a `completed` order. |

### Admin scripts (in `scripts/`)

Run these locally with a configured `.env`:

| Script | Purpose |
|---|---|
| `init_db_manual.py` | Creates all DB tables. Run once on new environment. |
| `check_orders.py` | Lists recent orders with status, email, style, amount |
| `check_replicate_predictions.py` | Lists recent Replicate predictions |
| `get_last_result_urls.py` | Prints result URLs of the last completed order |
| `view_order_results.py` | Opens result images in browser |
| `test_replicate.py` | Manual end-to-end test of Replicate integration |
| `setup_*_pack.py` | One-time setup scripts for each pack (historical, not needed for new deploys) |

### Internal marketing tool

`/marketing` — upload any photo, select any of the 90 paintings, get a single high-quality style transfer result. Uses `POST /api/marketing/style-transfer`. Not linked from the public site.

---

## 17. Deployment – Render.com

### render.yaml blueprint

The `render.yaml` file provisions:
1. A free PostgreSQL database named `artify-db`
2. A Python web service named `artify`

```yaml
databases:
  - name: artify-db
    databaseName: artify
    user: artify
    plan: free

services:
  - type: web
    name: artify
    runtime: python
    buildCommand: pip install -r requirements.txt
    preDeployCommand: python scripts/init_db_manual.py
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Deployment steps

1. Push code to GitHub.
2. In Render dashboard: New → Blueprint → connect repo → Render reads `render.yaml`.
3. After initial deploy, set these env vars in the Render dashboard (they are marked `sync: false` in the blueprint, meaning you must set them manually):

| Env Var | Where to get it |
|---|---|
| `OPENAI_API_KEY` | platform.openai.com → API keys |
| `REPLICATE_API_TOKEN` | replicate.com → account settings |
| `PUBLIC_BASE_URL` | Your Render service URL, e.g. `https://artify.onrender.com` |
| `STRIPE_SECRET_KEY` | Stripe dashboard → Developers → API keys |
| `STRIPE_PUBLISHABLE_KEY` | Same |
| `STRIPE_WEBHOOK_SECRET` | Stripe dashboard → Developers → Webhooks → endpoint signing secret |
| `RESEND_API_KEY` | resend.com → API keys |
| `FROM_EMAIL` | Your verified sender email in Resend |

4. Register the Stripe webhook:
   - Stripe dashboard → Developers → Webhooks → Add endpoint
   - URL: `https://{your-render-domain}/api/stripe/webhook`
   - Event: `checkout.session.completed`
   - Copy the signing secret to `STRIPE_WEBHOOK_SECRET`

5. `DATABASE_URL` is automatically injected from the `artify-db` database.

### Important Render notes

- **Ephemeral disk**: Render's free tier does not have a persistent disk. Uploaded photos and result images written to disk will be lost on redeploy. This is why both are also stored in PostgreSQL (`art_order_source_images` and `art_order_result_images`). The app always tries DB first, then disk.
- **Free tier sleep**: The free web service sleeps after 15 minutes of inactivity. The first request after sleep takes ~30s. Consider upgrading to a paid plan for production.
- **Pre-deploy command**: `python scripts/init_db_manual.py` runs before each deploy to apply any new DB migrations.

---

## 18. Key Conventions & Rules

These are non-negotiable rules that must be followed when editing any file in this project.

### HTML structure

1. **Promo banner must come before the header** in every HTML file. The order is always: promo banner → header → main → footer → menu overlay → scripts.
2. **Header class must be exactly** `class="header header-scroll-fade" id="main-header"` on every page. This is required for the scroll fade JS in `script.js` to work.
3. **`script.js` must be loaded on every page** (before page-specific scripts). Without it, the hamburger menu and header scroll effect will not work.
4. **Mobile menu overlay** (`<div class="menu-overlay" id="menu-overlay">`) must be present on every page for the hamburger button to function.

### CSS

5. **Never hardcode colors** — always use CSS variables from `styles.css` (e.g. `var(--primary)`, `var(--bg)`, `var(--text)`).
6. **All new page-specific styles** go in the page's own CSS file, not in `styles.css`. Only truly global styles belong in `styles.css`.

### JavaScript

7. **No jQuery or external JS frameworks** — all JS is vanilla ES5/ES6.
8. **State between pages is URL params + sessionStorage only** — no cookies, no localStorage, no server-side sessions.

### Content & Formatting

9. **All UI text is in Romanian.** Error messages, labels, button text, email subjects — everything.
10. **Prices use Romanian decimal comma**: `9,99 Lei` not `9.99 Lei`.
11. **Style IDs 13, 14, 15 are active**. IDs 16, 17, 18 are "coming soon" — they have `"comingSoon": true` in `styles-data.js` and are not processed by the backend.

### Backend

12. **Never change style pack IDs** (13–18) without updating both `styles-data.js` (frontend) and `main.py` (backend). They must always match.
13. **Never change painting filenames** without updating the corresponding `PACK_PROMPTS` and `PACK_LABELS` arrays in `main.py`. The filename index maps directly to the array index.
14. **`PUBLIC_BASE_URL` must be set** in production. Without it, image URLs in emails will be broken and result images will not be served correctly.
15. **`init_db()` is idempotent** — safe to run multiple times. It uses `CREATE TABLE IF NOT EXISTS` and `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`.
