"""Print direct image URLs from the last order that has result_urls. Uses .env DATABASE_URL."""
import json
import os
import sys

def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.isfile(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    v = v.strip().strip('"').strip("'")
                    os.environ[k.strip()] = v

_load_env()

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
except ImportError:
    print("Install: pip install sqlalchemy psycopg2-binary")
    sys.exit(1)

def main():
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("No DATABASE_URL in .env")
        return 1
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    engine = create_engine(url)
    Session = sessionmaker(bind=engine)
    db = Session()
    # First try result_urls
    r = db.execute(text("""
        SELECT order_id, result_urls, replicate_prediction_details FROM art_orders
        WHERE (result_urls IS NOT NULL AND result_urls != '' AND result_urls != '[]')
           OR (replicate_prediction_details IS NOT NULL AND replicate_prediction_details != '' AND replicate_prediction_details != '[]')
        ORDER BY id DESC LIMIT 1
    """))
    row = r.fetchone()
    db.close()
    if not row:
        print("No order with result images found.")
        return 0
    order_id, result_urls, replicate_prediction_details = row
    urls = []
    if result_urls:
        try:
            urls = json.loads(result_urls) if isinstance(result_urls, str) else result_urls
        except Exception:
            pass
    if not urls and replicate_prediction_details:
        try:
            details = json.loads(replicate_prediction_details) if isinstance(replicate_prediction_details, str) else replicate_prediction_details
            if isinstance(details, list):
                for item in details:
                    if isinstance(item, dict) and item.get("result_url"):
                        urls.append(item["result_url"])
        except Exception:
            pass
    print("Order:", order_id)
    if not urls:
        print("No image URLs in result_urls or replicate_prediction_details.")
        return 0
    print("\nImage URLs (direct, one per line):")
    for u in urls:
        print(u)
    return 0

if __name__ == "__main__":
    sys.exit(main())
