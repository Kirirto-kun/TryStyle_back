from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class WaitListItemBase(BaseModel):
    image_url: str
    status: Optional[str] = "pending"
    try_on_url: Optional[str] = None


class WaitListItemCreate(WaitListItemBase):
    pass


class WaitListScreenshotUpload(BaseModel):
    """Schema used when a browser extension posts a base64 screenshot."""

    image_base64: str


class TryOnRequest(BaseModel):
    """Schema for try-on request with user's photo."""
    image_base64: str
    waitlist_item_id: int


class WaitListItemResponse(WaitListItemBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True 