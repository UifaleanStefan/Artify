# Deploying Artify – Database & Backend

## Overview

Artify uses **its own** PostgreSQL database and backend, **separate from Magic Moments** (or any other project).

- **Database**: Dedicated PostgreSQL for Artify. The blueprint creates it; tables (`art_orders`) are created automatically when the backend starts.
- **Backend**: FastAPI app; deploy it as a web service with the Artify database URL.

---

## 1. Database (Artify-only)

Artify must **not** use the Magic Moments database. Use either:

- **Blueprint (recommended)**: The included `render.yaml` creates a PostgreSQL database named **artify-db** and wires it to the Artify web service. `DATABASE_URL` is set automatically from that database.
- **Manual**: Create a **new** PostgreSQL instance on Render (or elsewhere) for Artify only. Copy its connection string and set `DATABASE_URL` in the Artify service environment.

(Do not use the same database as Magic Moments.)
- **Tables**: The `art_orders` table is created on **first backend startup** by `init_db()` in `main.py`. No migrations to run manually. If you already had `art_orders` from before the Masters-pack change, add the new column: `ALTER TABLE art_orders ADD COLUMN IF NOT EXISTS style_image_urls TEXT;`

For manual setup: copy the Artify Postgres Internal URL and set it as `DATABASE_URL` in the Artify service environment (see Backend section below).  
   If the URL uses `postgres://`, the app will rewrite it to `postgresql://` automatically.

---

## 2. Backend

### Environment variables (required in production)

Set these in your hosting platform (Render, Railway, etc.):

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | **Yes** | PostgreSQL connection string (e.g. from Render dashboard). |
| `REPLICATE_API_TOKEN` | **Yes** (for style transfer) | From [Replicate](https://replicate.com/account/api-tokens). |
| `PUBLIC_BASE_URL` | Optional | Public URL of your app (e.g. `https://your-app.onrender.com`) for links in emails. |
| `UPLOAD_DIR` | Optional | Directory for uploads; default is a temp dir. |

Do **not** commit `.env` or put secrets in the repo. Configure them in the host’s **Environment** / **Secrets** UI.

### Run locally (test before deploy)

```bash
# From project root, with .env present
python -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

Then open http://127.0.0.1:8001 . The first run will create `art_orders` if the DB is empty.

### Deploy on Render (separate Artify DB + backend)

**Option A – Blueprint (one click)**  
1. In Render: **New** → **Blueprint**; connect this repo.  
2. Render will create **artify-db** (PostgreSQL) and **artify** (Web Service). `DATABASE_URL` is set from the new DB automatically.  
3. In the **artify** service → **Environment**: add `REPLICATE_API_TOKEN`; optionally `PUBLIC_BASE_URL` (your Artify app URL).  
4. Deploy. On first start the app will create the `art_orders` table in the Artify database.

**Option B – Manual**  
1. Create a **PostgreSQL** instance (name it e.g. Artify DB); do **not** reuse the Magic Moments DB.  
2. **New Web Service** → connect your repo.  
3. Build: `pip install -r requirements.txt`. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`.  
4. Environment: set `DATABASE_URL` to the **Artify** Postgres Internal URL, add `REPLICATE_API_TOKEN`, optionally `PUBLIC_BASE_URL`.  
5. Deploy.

You can use the included **Procfile** or **render.yaml** as a reference.

### Deploy elsewhere (Railway, Fly.io, Docker, etc.)

- **Start command**:  
  `uvicorn main:app --host 0.0.0.0 --port 8000`  
  (Use the port your platform expects, e.g. `$PORT` on Railway.)
- Set the same **env vars** as above (`DATABASE_URL`, `REPLICATE_API_TOKEN`, etc.).

---

## 3. Render blueprint (separate Artify DB + backend)

**render.yaml** defines a **dedicated** PostgreSQL database (**artify-db**) and the Artify web service. In Render:

- Create a **Blueprint** and point it at this repo, or
- Create a **Web Service** manually and use the same build/start commands and env vars as in section 2.

---

## 4. After deploy

- Open your app URL; the landing and styles pages should load.
- Go through **Style → Upload → Details → Billing → Payment**; an order should be stored in `art_orders` and (with a valid `REPLICATE_API_TOKEN`) style transfer can run.
- If something fails, check the service logs and that `DATABASE_URL` and `REPLICATE_API_TOKEN` are set correctly.
