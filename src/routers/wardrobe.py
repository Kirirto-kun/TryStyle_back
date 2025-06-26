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
from src.utils.firebase_storage import upload_image_to_firebase_async, delete_image_from_firebase_async
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
            image_url = await upload_image_to_firebase_async(img_bytes, file_name)
            
            # Analyze image using Azure OpenAI
            analysis = await analyze_image(image_url)
            
            # Filter out None values from features to prevent validation errors
            features = [f for f in analysis.get("features", []) if f is not None and isinstance(f, str)]
            
            # Create database entry
            db_item = ClothingItem(
                name=analysis["name"],  # Use the name from analysis
                image_url=image_url,
                category=analysis["category"],
                features=features,
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
    
    # Clean up features to remove None values for existing items
    for item in items:
        if item.features:
            item.features = [f for f in item.features if f is not None and isinstance(f, str)]
    
    return items

@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clothing_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a clothing item from the wardrobe.
    """
    item = db.query(ClothingItem).filter(
        ClothingItem.id == item_id,
        ClothingItem.user_id == current_user.id
    ).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clothing item not found"
        )

    # Delete image from Firebase
    if item.image_url:
        await delete_image_from_firebase_async(item.image_url)

    # Delete from database
    db.delete(item)
    db.commit()

    return 