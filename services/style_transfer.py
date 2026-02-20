"""
Style transfer service – submits job and polls for result.
"""
import logging
from typing import Optional, Tuple

from clients.replicate_client import ReplicateClient

logger = logging.getLogger(__name__)


class StyleTransferService:
    def __init__(self, provider: ReplicateClient):
        self.provider = provider

    async def transfer_style(
        self,
        image_url: str,
        style_image_url: str,
    ) -> Tuple[str, str]:
        """Run style transfer. Returns (result_url, job_id)."""
        job_id = self.provider.submit_style_transfer(image_url, style_image_url)
        logger.info(
            "Style transfer submitted",
            extra={"job_id": job_id, "image_url": image_url[:80]},
        )
        result_url = self.provider.poll_result(job_id)
        logger.info(
            "Style transfer completed",
            extra={"job_id": job_id, "result_url": result_url[:80]},
        )
        return result_url, job_id
