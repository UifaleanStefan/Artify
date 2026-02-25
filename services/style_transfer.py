"""
Style transfer service – submits job and polls for result.
Supports OpenAI (prompt-based) and Replicate (reference-image) providers.
"""
import asyncio
import logging
from typing import Optional, Tuple, Union

from clients.openai_stylize_client import OpenAIStylizeClient
from clients.replicate_client import ReplicateClient

logger = logging.getLogger(__name__)


class StyleTransferService:
    def __init__(self, provider: Union[ReplicateClient, OpenAIStylizeClient]):
        self.provider = provider

    def _transfer_style_sync(
        self,
        image_url: str,
        style_image_url: Optional[str] = None,
        structure_denoising_strength: float = 0.7,
        style_prompt: Optional[str] = None,
    ) -> Tuple[Union[str, dict], str]:
        """Blocking provider calls. Returns (result_url or {content, content_type}, job_id)."""
        if isinstance(self.provider, OpenAIStylizeClient):
            if not style_prompt:
                raise ValueError("style_prompt required when using OpenAI provider")
            content, content_type = self.provider.stylize(image_url, style_prompt)
            logger.info(
                "OpenAI style transfer completed",
                extra={"image_url": image_url[:80]},
            )
            return {"content": content, "content_type": content_type}, "openai"
        else:
            if not style_image_url:
                raise ValueError("style_image_url required when using Replicate provider")
            job_id = self.provider.submit_style_transfer(
                image_url, style_image_url, structure_denoising_strength
            )
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
        style_image_url: Optional[str] = None,
        structure_denoising_strength: float = 0.7,
        style_prompt: Optional[str] = None,
    ) -> Tuple[Union[str, dict], str]:
        """Synchronous style transfer call for worker threads/background processing."""
        return self._transfer_style_sync(
            image_url,
            style_image_url,
            structure_denoising_strength,
            style_prompt,
        )

    async def transfer_style(
        self,
        image_url: str,
        style_image_url: Optional[str] = None,
        structure_denoising_strength: float = 0.7,
        style_prompt: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Run style transfer without blocking event loop."""
        return await asyncio.to_thread(
            self._transfer_style_sync,
            image_url,
            style_image_url,
            structure_denoising_strength,
            style_prompt,
        )
