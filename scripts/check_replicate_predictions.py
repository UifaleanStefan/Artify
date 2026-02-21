"""
Query Replicate API for recent predictions to debug stuck orders.
Run from project root with REPLICATE_API_TOKEN in .env.
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(env_path):
    for line in open(env_path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            v = v.split("#")[0].strip().strip('"').strip("'")
            os.environ.setdefault(k.strip(), v)

from clients.replicate_client import ReplicateClient, StyleTransferError


def main():
    token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not token:
        print("ERROR: Set REPLICATE_API_TOKEN in .env")
        return 1

    client = ReplicateClient(api_token=token)
    print("Fetching recent Replicate predictions (most recent first)...\n")

    try:
        results = client.list_predictions()
    except StyleTransferError as e:
        print("API error:", e)
        return 1

    # Prefer fofr/style-transfer to match our jobs
    style_transfer_version_prefix = "f1023890703bc0a5a3a2c21b5e498833be5f6ef6e70e9daf6b9b3a4fd8309cf0"
    for i, p in enumerate(results[:30]):
        pid = p.get("id", "")
        status = p.get("status", "?")
        version = p.get("version", "") or ""
        is_ours = style_transfer_version_prefix in version or "fofr" in (p.get("model") or "")
        created = p.get("created_at", "")[:19] if p.get("created_at") else ""
        completed = (p.get("completed_at") or "")[:19] if p.get("completed_at") else ""
        error = (p.get("error") or "")[:80] if p.get("error") else ""
        metrics = p.get("metrics") or {}

        tag = " [fofr/style-transfer]" if is_ours else ""
        print(f"{i+1}. {pid}{tag}")
        print(f"   status: {status}  created: {created}  completed: {completed}")
        if metrics:
            print(f"   metrics: {metrics}")
        if error:
            print(f"   error: {error}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
