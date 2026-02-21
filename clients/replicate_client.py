"""
Replicate API client for style transfer.
"""
import logging
import time
from typing import Any, Dict, List, Optional

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
        rate_limit_retries: int = 4,
        rate_limit_base_wait: float = 15.0,
    ):
        self.api_token = api_token
        self.base_url = "https://api.replicate.com/v1"
        self.timeout_seconds = timeout_seconds
        self.polling_timeout = polling_timeout_seconds
        self.polling_interval = polling_interval_seconds
        self.rate_limit_retries = rate_limit_retries
        self.rate_limit_base_wait = rate_limit_base_wait

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
                "prompt": "Adapt the style of the style image to the structure image, keeping the brush strokes and brush details while emphasizing the features of the structure image, adapting them to the time period and style of the style image. Very important to keep the features in the structure image, so people are recognizable.",
                "structure_denoising_strength": 1,
                "output_format": "webp",
                "output_quality": 80,
                "number_of_images": 1,
            },
        }
        for attempt in range(self.rate_limit_retries):
            with httpx.Client(timeout=self.timeout_seconds) as client:
                r = client.post(url, json=payload, headers=self._headers())
                if r.status_code == 429:
                    wait = self.rate_limit_base_wait * (2 ** attempt)
                    if attempt < self.rate_limit_retries - 1:
                        logger.warning(
                            "Replicate rate limit (429), waiting %.0fs before retry %d/%d",
                            wait,
                            attempt + 1,
                            self.rate_limit_retries - 1,
                        )
                        time.sleep(wait)
                        continue
                    raise StyleTransferRateLimit("Rate limit exceeded after retries")
                if r.status_code >= 400:
                    raise StyleTransferError(f"Replicate API error {r.status_code}: {r.text}")
                data = r.json()
                prediction_id = data.get("id")
                if not prediction_id:
                    raise StyleTransferError("No prediction ID returned")
                logger.info(f"Style transfer job submitted: {prediction_id}")
                return prediction_id
        raise StyleTransferRateLimit("Rate limit exceeded")

    def get_prediction(self, prediction_id: str) -> Dict[str, Any]:
        """Get a single prediction by ID. Returns full API response."""
        url = f"{self.base_url}/predictions/{prediction_id}"
        with httpx.Client(timeout=self.timeout_seconds) as client:
            r = client.get(url, headers=self._headers())
            if r.status_code >= 400:
                raise StyleTransferError(f"Get prediction error {r.status_code}: {r.text}")
            return r.json()

    def list_predictions(self) -> List[Dict[str, Any]]:
        """List recent predictions (most recent first, 100 per page). Returns list of prediction objects."""
        url = f"{self.base_url}/predictions"
        with httpx.Client(timeout=self.timeout_seconds) as client:
            r = client.get(url, headers=self._headers())
            if r.status_code >= 400:
                raise StyleTransferError(f"List predictions error {r.status_code}: {r.text}")
            data = r.json()
            return data.get("results", [])

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
                    if isinstance(output, list) and len(output) > 0:
                        first = output[0]
                        if isinstance(first, str):
                            return first
                        if isinstance(first, dict) and first.get("url"):
                            return first["url"]
                    if isinstance(output, str):
                        return output
                    raise StyleTransferError(f"Unexpected output format: {output}")
                if status == "failed":
                    error = data.get("error", "Unknown error")
                    raise StyleTransferError(f"Style transfer failed: {error}")
                if status == "canceled":
                    raise StyleTransferError("Style transfer was canceled")
                time.sleep(self.polling_interval)
