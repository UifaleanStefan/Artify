"""
OpenAI image edit API client for style transfer.
Uses POST /v1/images/edits with text prompts (no reference image).
"""
import base64
import logging
import time
from typing import Any, Dict, Optional, Tuple

import httpx

from .replicate_client import StyleTransferError, StyleTransferRateLimit

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.openai.com"


class OpenAIStylizeClient:
    """Client for OpenAI POST /v1/images/edits (image edit with style prompt)."""

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        timeout_seconds: int = 120,
        model: str = "gpt-image-1.5",
        quality: str = "medium",
        output_format: str = "jpeg",
        input_fidelity: str = "high",
        rate_limit_retries: int = 4,
        rate_limit_base_wait: float = 15.0,
    ):
        self.api_key = api_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.model = model
        self.quality = quality
        self.output_format = output_format
        self.input_fidelity = input_fidelity
        self.rate_limit_retries = rate_limit_retries
        self.rate_limit_base_wait = rate_limit_base_wait

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def stylize(
        self,
        image_url: str,
        prompt: str,
        quality: Optional[str] = None,
        output_format: Optional[str] = None,
        input_fidelity: Optional[str] = None,
    ) -> Tuple[bytes, str]:
        """
        Apply style transfer using image edit API. Returns (image_bytes, content_type).
        GPT models return b64_json; we decode and return raw bytes.
        """
        if not image_url.startswith("https://"):
            raise StyleTransferError(
                "Image URL must be public HTTPS (set PUBLIC_BASE_URL on the server)."
            )
        quality = quality or self.quality
        output_format = output_format or self.output_format
        input_fidelity = input_fidelity or self.input_fidelity
        # gpt-image-1-mini does not support input_fidelity="high"; fall back to "low"
        if self.model == "gpt-image-1-mini" and input_fidelity == "high":
            input_fidelity = "low"

        url = f"{self.base_url}/v1/images/edits"
        payload = {
            "images": [{"image_url": image_url}],
            "prompt": prompt,
            "model": self.model,
            "quality": quality,
            "output_format": output_format,
            "input_fidelity": input_fidelity,
            "moderation": "low",  # Less restrictive; reduces false positives on portraits
            "n": 1,
            "size": "1024x1024",
        }

        for attempt in range(self.rate_limit_retries):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    r = client.post(url, json=payload, headers=self._headers())

                if r.status_code in (429, 500, 502, 503, 504):
                    wait = self.rate_limit_base_wait * (2**attempt)
                    if attempt < self.rate_limit_retries - 1:
                        logger.warning(
                            "OpenAI image edit transient error (%s), waiting %.0fs before retry %d/%d",
                            r.status_code,
                            wait,
                            attempt + 1,
                            self.rate_limit_retries,
                        )
                        time.sleep(wait)
                        continue
                    if r.status_code == 429:
                        raise StyleTransferRateLimit("Rate limit exceeded after retries")
                    raise StyleTransferError(
                        f"OpenAI image edit transient error {r.status_code} after retries: {r.text[:500]}"
                    )
                if r.status_code >= 400:
                    raise StyleTransferError(
                        f"OpenAI image edit API error {r.status_code}: {r.text[:500]}"
                    )

                resp = r.json()
                data = resp.get("data") or []
                if not data:
                    err = resp.get("error", {})
                    msg = err.get("message", str(err)) if isinstance(err, dict) else str(resp)
                    raise StyleTransferError(f"OpenAI image edit failed: {msg}")

                first = data[0]
                b64_json = first.get("b64_json")
                if b64_json:
                    content = base64.b64decode(b64_json)
                    content_type = f"image/{output_format}" if output_format != "jpeg" else "image/jpeg"
                    logger.info("OpenAI image edit completed (b64 decoded)")
                    return content, content_type

                result_url = first.get("url")
                if result_url:
                    with httpx.Client(timeout=45) as client:
                        img_r = client.get(result_url)
                    if img_r.status_code >= 400:
                        raise StyleTransferError(f"Failed to fetch result image: {img_r.status_code}")
                    content_type = img_r.headers.get("content-type", "image/jpeg").split(";")[0].strip()
                    return img_r.content, content_type

                raise StyleTransferError(f"Unexpected OpenAI response format: {first}")

            except httpx.RequestError as e:
                wait = self.rate_limit_base_wait * (2**attempt)
                if attempt < self.rate_limit_retries - 1:
                    logger.warning(
                        "OpenAI image edit network error, waiting %.0fs before retry %d/%d: %s",
                        wait,
                        attempt + 1,
                        self.rate_limit_retries,
                        e,
                    )
                    time.sleep(wait)
                    continue
                raise StyleTransferError(f"OpenAI request failed after retries: {e}")

        raise StyleTransferRateLimit("Rate limit exceeded")

    def get_prediction(self, job_id: str) -> Dict[str, Any]:
        """OpenAI edit is synchronous; no prediction object. Return minimal dict for compatibility."""
        return {"id": job_id, "status": "succeeded", "result_url": job_id}
