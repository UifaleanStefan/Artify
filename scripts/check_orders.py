"""Quick script to print recent orders and their Replicate/result status."""
import json
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(env_path):
    for line in open(env_path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            v = v.split("#")[0].strip().strip('"').strip("'")
            os.environ.setdefault(k.strip(), v)

from database import SessionLocal, Order

def main():
    db = SessionLocal()
    orders = db.query(Order).order_by(Order.id.desc()).limit(15).all()
    print("Recent orders (newest first):")
    print("-" * 80)
    for o in orders:
        urls = o.result_urls
        n = 0
        if urls:
            try:
                n = len(json.loads(urls))
            except Exception:
                n = 1 if urls else 0
        err = (o.style_transfer_error or "")[:80]
        print("order_id:", o.order_id)
        print("  status:", o.status, "| email:", (o.email or "")[:50])
        print("  result_urls:", "yes (%d image(s))" % n if o.result_urls else "no")
        if o.result_urls and n > 0:
            try:
                first = json.loads(o.result_urls)[0]
                print("  first_url:", first[:70] + "..." if len(first) > 70 else first)
            except Exception:
                pass
        if err:
            print("  error:", err)
        print()
    db.close()

if __name__ == "__main__":
    main()
