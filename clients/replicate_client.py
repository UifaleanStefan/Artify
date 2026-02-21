"""
Replicate API client for style transfer.
"""
import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class StyleTransferError(Exception):
    pass

class StyleTransferRateLimit(StyleTransferError):
    pass

class StyleTransferTimeout(StyleTransferError):
    pass


class ReplicateClient:
    def __init__(
        self,
        api_token: str,
        timeout_seconds: int = 120,
        polling_timeout_seconds: int = 300,
        polling_interval_seconds: int = 5,
    ):
        self.api_token = api_token
        self.base_url = "https://api.replicate.com/v1"
        self.timeout_seconds = timeout_seconds
        self.polling_timeout = polling_timeout_seconds
        self.polling_interval = polling_interval_seconds

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    # fofr/style-transfer: structure_image = pose/face to keep, style_image = artistic style
    STYLE_TRANSFER_VERSION = "fofr/style-transfer:f1023890703bc0a5a3a2c21b5e498833be5f6ef6e70e9daf6b9b3a4fd8309cf0"

    def submit_style_transfer(self, image_url: str, style_image_url: str) -> str:
        """Submit a style transfer job. Returns prediction ID."""
        if not image_url.startswith("https://") or not style_image_url.startswith("https://"):
            raise StyleTransferError(
                "Image URLs must be public HTTPS URLs (set PUBLIC_BASE_URL on the server that creates orders)."
            )
        url = f"{self.base_url}/predictions"
        payload = {
            "version": self.STYLE_TRANSFER_VERSION,
            "input": {
                "structure_image": image_url,
                "style_image": style_image_url,
                "structure_denoising_strength": 0.65,
                "output_format": "webp",
                "output_quality": 80,
                "number_of_images": 1,
            },
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            r = client.post(url, json=payload, headers=self._headers())
            if r.status_code == 429:
                raise StyleTransferRateLimit("Rate limit exceeded")
            if r.status_code >= 400:
                raise StyleTransferError(f"Replicate API error {r.status_code}: {r.text}")
            data = r.json()
            prediction_id = data.get("id")
            if not prediction_id:
                raise StyleTransferError("No prediction ID returned")
            logger.info(f"Style transfer job submitted: {prediction_id}")
            return prediction_id

    def poll_result(self, prediction_id: str) -> str:
        """Poll until prediction completes. Returns output URL."""
        url = f"{self.base_url}/predictions/{prediction_id}"
        start = time.time()
        with httpx.Client(timeout=self.timeout_seconds) as client:
            while True:
                if time.time() - start > self.polling_timeout:
                    raise StyleTransferTimeout(
                        f"Polling timed out after {self.polling_timeout}s"
                    )
                r = client.get(url, headers=self._headers())
                if r.status_code >= 400:
                    raise StyleTransferError(f"Poll error {r.status_code}: {r.text}")
                data = r.json()
                status = data.get("status", "")
                if status == "succeeded":
                    output = data.get("output")
                    if isinstance(output, list):
                        return output[0]
                    if isinstance(output, str):
                        return output
                    raise StyleTransferError(f"Unexpected output format: {output}")
                if status == "failed":
                    error = data.get("error", "Unknown error")
                    raise StyleTransferError(f"Style transfer failed: {error}")
                if status == "canceled":
                    raise StyleTransferError("Style transfer was canceled")
                time.sleep(self.polling_interval)
