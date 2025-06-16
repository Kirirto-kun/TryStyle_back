from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import base64
import uuid
from src.database import get_db
from src.models.clothing import ClothingItem
from src.models.user import User
from src.schemas.clothing import ClothingItemCreate, ClothingItemResponse
from src.utils.auth import get_current_user
from src.utils.firebase_storage import upload_image_to_firebase
from src.schemas.clothing import PhotoUpload
from src.utils.analyze_image import analyze_image

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])

@router.post("/items", response_model=List[ClothingItemResponse])
async def create_clothing_items(
    photos: List[PhotoUpload],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    created_items = []
    
    for photo in photos:
        try:
            # Decode base64 image
            img_bytes = base64.b64decode(photo.image_base64.split(",")[-1])
            
            # Upload to Firebase Storage
            file_name = f"{uuid.uuid4()}.png"
            image_url = upload_image_to_firebase(img_bytes, file_name)
            
            # Analyze image using Azure OpenAI
            analysis = await analyze_image(image_url)
            
            # Create database entry
            db_item = ClothingItem(
                name=analysis["category"],  # Use category as name
                image_url=image_url,
                category=analysis["category"],
                features=analysis["features"],
                user_id=current_user.id
            )
            db.add(db_item)
            created_items.append(db_item)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process image: {str(e)}"
            )
    
    db.commit()
    for item in created_items:
        db.refresh(item)
    
    return created_items

@router.get("/items", response_model=List[ClothingItemResponse])
async def get_my_clothing_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    items = db.query(ClothingItem).filter(ClothingItem.user_id == current_user.id).all()
    return items 