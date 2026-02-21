"""
Fetch order status from the API and print/open result image URLs.
Usage: python scripts/view_order_results.py ART-1771678963768-1E071781
       python scripts/view_order_results.py ART-1771678963768-1E071781 --open
Use --base https://artify-b442.onrender.com for production (default: http://127.0.0.1:8000)
"""
import argparse
import json
import sys

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)


def main():
    p = argparse.ArgumentParser(description="View order result URLs from API")
    p.add_argument("order_id", help="Order ID (e.g. ART-1771678963768-1E071781)")
    p.add_argument("--base", default="https://artify-b442.onrender.com", help="Base URL of the API")
    p.add_argument("--open", action="store_true", dest="open_browser", help="Print URLs so you can open in browser")
    args = p.parse_args()

    base = args.base.rstrip("/")
    url = f"{base}/api/orders/{args.order_id}/status"

    print(f"Fetching: {url}")
    try:
        r = httpx.get(url, timeout=15)
    except Exception as e:
        print("Request failed:", e)
        sys.exit(1)

    if r.status_code == 404:
        print("404 – Order not found. Check the order_id and that you're using the right --base URL.")
        sys.exit(1)
    if r.status_code != 200:
        print(f"Error {r.status_code}:", r.text[:300])
        sys.exit(1)

    data = r.json()
    status = data.get("status", "")
    result_urls_raw = data.get("result_urls")
    error = data.get("error")

    print(f"Order: {data.get('order_id')}")
    print(f"Status: {status}")
    if error:
        print(f"Error: {error}")

    urls = []
    if result_urls_raw:
        try:
            urls = json.loads(result_urls_raw) if isinstance(result_urls_raw, str) else (result_urls_raw or [])
        except Exception:
            urls = []

    if not urls:
        print("No result URLs yet (order may still be processing, or it failed/was interrupted).")
        print("Run: python scripts/check_orders.py  to see status of recent orders.")
        sys.exit(0)

    print(f"\nResult images ({len(urls)}):")
    for i, u in enumerate(urls, 1):
        print(f"  {i}. {u}")
    if args.open_browser:
        print("\nOpen any URL above in your browser to view the image.")


if __name__ == "__main__":
    main()
