"""
Style transfer service – submits job and polls for result.
"""
import asyncio
import logging
from typing import Tuple

from clients.replicate_client import ReplicateClient

logger = logging.getLogger(__name__)


class StyleTransferService:
    def __init__(self, provider: ReplicateClient):
        self.provider = provider

    def _transfer_style_sync(self, image_url: str, style_image_url: str) -> Tuple[str, str]:
        """Blocking provider calls wrapped for thread execution."""
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

    def transfer_style_sync(
        self,
        image_url: str,
        style_image_url: str,
    ) -> Tuple[str, str]:
        """Synchronous style transfer call for worker threads/background processing."""
        return self._transfer_style_sync(image_url, style_image_url)

    async def transfer_style(
        self,
        image_url: str,
        style_image_url: str,
    ) -> Tuple[str, str]:
        """Run style transfer without blocking event loop."""
        return await asyncio.to_thread(self._transfer_style_sync, image_url, style_image_url)
