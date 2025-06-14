from pydantic import BaseModel
from typing import Optional, Dict

class ClothingItemBase(BaseModel):
    name: str
    image_url: str
    features: Optional[Dict] = {}

class ClothingItemCreate(ClothingItemBase):
    pass

class ClothingItemResponse(ClothingItemBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True 

class PhotoUpload(BaseModel):
    image_base64: str