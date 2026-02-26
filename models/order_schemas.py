from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class OrderCreateRequest(BaseModel):
    email: EmailStr
    style_id: int
    image_url: str
    portrait_mode: Optional[str] = "realistic"  # "realistic" -> 0.55, "artistic" -> 0.8
    pack_tier: Optional[int] = 5  # 5 portraits (9.99) or 15 portraits (19.99)
    billing_name: Optional[str] = None
    billing_address: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_zip: Optional[str] = None
    billing_country: Optional[str] = None


class OrderResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    order_id: str
    status: str
    email: str
    style_id: Optional[int] = None
    style_name: Optional[str] = None
    image_url: str
    result_urls: Optional[str] = None
    style_transfer_job_id: Optional[str] = None
    replicate_prediction_details: Optional[str] = None
    amount: Optional[float] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class OrderStatusResponse(BaseModel):
    order_id: str
    status: str
    result_urls: Optional[str] = None
    result_labels: Optional[list[list[str]]] = None
    style_id: Optional[int] = None
    style_name: Optional[str] = None
    initial_image_url: Optional[str] = None
    style_image_urls: Optional[str] = None
    replicate_prediction_details: Optional[str] = None
    error: Optional[str] = None
