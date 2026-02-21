"""
Test Replicate style-transfer API locally.
Uses public HTTPS URLs so Replicate can fetch them.
Run from project root with REPLICATE_API_TOKEN in .env (or env).
"""
import os
import sys

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

from clients.replicate_client import ReplicateClient, StyleTransferError, StyleTransferRateLimit, StyleTransferTimeout


# Public image URLs Replicate can fetch (HTTPS)
# Structure: one face/portrait. Style: one Masters reference.
PUBLIC_STRUCTURE_IMAGE = (
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=512"
)  # portrait
PUBLIC_STYLE_IMAGE = (
    "https://artify-b442.onrender.com/static/landing/styles/masters/masters-01.jpg"
)


def main():
    token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not token:
        print("ERROR: Set REPLICATE_API_TOKEN in .env or environment")
        sys.exit(1)

    base_url = os.environ.get("PUBLIC_BASE_URL", "").strip()
    if not base_url:
        print("WARNING: PUBLIC_BASE_URL not set. Orders created by this server will have non-HTTPS style URLs and Replicate will reject them.")
    else:
        resolved = (base_url.rstrip("/") + "/static/landing/styles/masters/masters-01.jpg") if base_url else ""
        if resolved.startswith("https://"):
            print("PUBLIC_BASE_URL is set; order style URLs will resolve to HTTPS.")
        else:
            print("WARNING: PUBLIC_BASE_URL should be https://... so Replicate can fetch style images.")

    print("Testing Replicate style-transfer API...")
    print("  structure_image (portrait):", PUBLIC_STRUCTURE_IMAGE[:60] + "...")
    print("  style_image:", PUBLIC_STYLE_IMAGE)
    print()

    client = ReplicateClient(
        api_token=token,
        timeout_seconds=120,
        polling_timeout_seconds=300,
        polling_interval_seconds=5,
    )

    try:
        prediction_id = client.submit_style_transfer(
            image_url=PUBLIC_STRUCTURE_IMAGE,
            style_image_url=PUBLIC_STYLE_IMAGE,
        )
        print("Submitted. Prediction ID:", prediction_id)
        print("Polling for result (may take 1–3 min)...")
        result_url = client.poll_result(prediction_id)
        print("SUCCESS. Result URL:", result_url)
        return 0
    except StyleTransferRateLimit as e:
        print("RATE LIMIT:", e)
        return 1
    except StyleTransferTimeout as e:
        print("TIMEOUT:", e)
        return 1
    except StyleTransferError as e:
        print("ERROR:", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
