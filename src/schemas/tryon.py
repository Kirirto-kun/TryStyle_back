from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from fastapi import UploadFile, File

class TryOnBase(BaseModel):
    clothing_image_url: str
    human_image_url: str
    result_url: Optional[str] = None

class TryOnCreate(BaseModel):
    clothing_image_base64: str
    human_image_base64: str

class TryOnResponse(TryOnBase):
    id: int
    user_id: int
    created_at: datetime
    status: str

    class Config:
        from_attributes = True

class TryOnRequest(BaseModel):
    clothing_image_base64: str
    human_image_base64: str 