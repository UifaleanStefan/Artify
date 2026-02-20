from typing import Optional
from pydantic import BaseModel, Field


class StyleTransferRequest(BaseModel):
    model_config = {"extra": "ignore"}
    image_url: str = Field(default="", description="URL of the user photo")
    style_id: int = Field(default=0, description="Art style ID")


class StyleTransferResponse(BaseModel):
    result_url: str = Field(..., description="URL of the stylized result image")
    job_id: Optional[str] = Field(None, description="Provider job ID")


class StyleTransferErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
