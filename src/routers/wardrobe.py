from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from src.database import get_db
from src.models.clothing import ClothingItem
from src.models.user import User
from src.schemas.clothing import ClothingItemCreate, ClothingItemResponse
from src.utils.auth import get_current_user

router = APIRouter(prefix="/wardrobe", tags=["wardrobe"])

@router.post("/items", response_model=ClothingItemResponse)
async def create_clothing_item(
    item: ClothingItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_item = ClothingItem(
        **item.model_dump(),
        user_id=current_user.id
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/items", response_model=List[ClothingItemResponse])
async def get_my_clothing_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    items = db.query(ClothingItem).filter(ClothingItem.user_id == current_user.id).all()
    return items 