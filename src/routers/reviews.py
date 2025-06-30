from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from typing import List, Optional
import logging
from datetime import datetime, timedelta

from src.database import get_db
from src.models.review import Review
from src.models.product import Product
from src.models.user import User
from src.schemas.review import (
    ReviewResponse, ReviewListResponse, ReviewCreate, ReviewUpdate, ReviewStatsResponse
)
from src.utils.auth import get_current_user

router = APIRouter(prefix="/reviews", tags=["reviews"])
logger = logging.getLogger(__name__)


@router.get("/product/{product_id}", response_model=ReviewListResponse)
async def get_product_reviews(
    product_id: int,
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(20, ge=1, le=100, description="Количество на странице"),
    sort_by: str = Query("created_at", description="Сортировка: created_at, rating"),
    sort_order: str = Query("desc", description="Порядок: asc, desc"),
    rating_filter: Optional[int] = Query(None, ge=1, le=5, description="Фильтр по рейтингу"),
    verified_only: bool = Query(False, description="Только проверенные отзывы"),
    db: Session = Depends(get_db)
):
    """Получить отзывы для конкретного товара"""
    
    # Проверяем существование товара
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    
    query = db.query(Review).filter(Review.product_id == product_id)
    
    # Фильтрация
    if rating_filter:
        query = query.filter(Review.rating == rating_filter)
    
    if verified_only:
        query = query.filter(Review.is_verified == True)
    
    # Сортировка
    sort_column = getattr(Review, sort_by, Review.created_at)
    if sort_order.lower() == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))
    
    # Пагинация
    total = query.count()
    reviews = query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Статистика рейтингов
    rating_stats = db.query(
        Review.rating,
        func.count(Review.id).label('count')
    ).filter(Review.product_id == product_id).group_by(Review.rating).all()
    
    rating_distribution = {i: 0 for i in range(1, 6)}
    total_ratings = 0
    for stat in rating_stats:
        rating_distribution[stat.rating] = stat.count
        total_ratings += stat.count
    
    # Средний рейтинг
    avg_rating = db.query(func.avg(Review.rating)).filter(Review.product_id == product_id).scalar() or 0.0
    
    return ReviewListResponse(
        reviews=reviews,
        total=total,
        page=page,
        per_page=per_page,
        average_rating=round(avg_rating, 2),
        rating_distribution=rating_distribution
    )


@router.get("/user/{user_id}", response_model=ReviewListResponse)
async def get_user_reviews(
    user_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Получить отзывы конкретного пользователя"""
    
    # Проверяем существование пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    query = db.query(Review).filter(Review.user_id == user_id).order_by(desc(Review.created_at))
    
    total = query.count()
    reviews = query.offset((page - 1) * per_page).limit(per_page).all()
    
    # Средний рейтинг пользователя
    avg_rating = db.query(func.avg(Review.rating)).filter(Review.user_id == user_id).scalar() or 0.0
    
    return ReviewListResponse(
        reviews=reviews,
        total=total,
        page=page,
        per_page=per_page,
        average_rating=round(avg_rating, 2),
        rating_distribution={}
    )


@router.post("/", response_model=ReviewResponse)
async def create_review(
    review_data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать новый отзыв"""
    
    # Проверяем существование товара
    product = db.query(Product).filter(Product.id == review_data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    
    # Проверяем, не оставлял ли пользователь уже отзыв на этот товар
    existing_review = db.query(Review).filter(
        Review.product_id == review_data.product_id,
        Review.user_id == current_user.id
    ).first()
    
    if existing_review:
        raise HTTPException(
            status_code=400, 
            detail="Вы уже оставили отзыв на этот товар"
        )
    
    # Создаем отзыв
    review = Review(
        **review_data.model_dump(),
        user_id=current_user.id
    )
    
    db.add(review)
    db.commit()
    db.refresh(review)
    
    # Обновляем рейтинг товара
    await update_product_rating(product.id, db)
    
    logger.info(f"Создан отзыв от пользователя {current_user.username} на товар {product.name}")
    
    return review


@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    review_data: ReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить отзыв (только автор может редактировать)"""
    
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Отзыв не найден")
    
    # Проверяем, что пользователь является автором отзыва
    if review.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Можно редактировать только свои отзывы")
    
    # Обновляем только переданные поля
    for field, value in review_data.model_dump(exclude_unset=True).items():
        setattr(review, field, value)
    
    db.commit()
    db.refresh(review)
    
    # Обновляем рейтинг товара
    await update_product_rating(review.product_id, db)
    
    logger.info(f"Обновлен отзыв {review_id}")
    
    return review


@router.delete("/{review_id}")
async def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить отзыв (только автор может удалить)"""
    
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Отзыв не найден")
    
    # Проверяем, что пользователь является автором отзыва
    if review.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Можно удалять только свои отзывы")
    
    product_id = review.product_id
    
    db.delete(review)
    db.commit()
    
    # Обновляем рейтинг товара
    await update_product_rating(product_id, db)
    
    logger.info(f"Удален отзыв {review_id}")
    
    return {"message": "Отзыв успешно удален"}


@router.get("/stats/product/{product_id}", response_model=ReviewStatsResponse)
async def get_product_review_stats(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Получить статистику отзывов для товара"""
    
    # Проверяем существование товара
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    
    # Общее количество отзывов
    total_reviews = db.query(Review).filter(Review.product_id == product_id).count()
    
    # Средний рейтинг
    avg_rating = db.query(func.avg(Review.rating)).filter(Review.product_id == product_id).scalar() or 0.0
    
    # Распределение рейтингов
    rating_stats = db.query(
        Review.rating,
        func.count(Review.id).label('count')
    ).filter(Review.product_id == product_id).group_by(Review.rating).all()
    
    rating_distribution = {i: 0 for i in range(1, 6)}
    for stat in rating_stats:
        rating_distribution[stat.rating] = stat.count
    
    # Количество проверенных отзывов
    verified_count = db.query(Review).filter(
        Review.product_id == product_id,
        Review.is_verified == True
    ).count()
    
    # Количество отзывов за последние 30 дней
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_count = db.query(Review).filter(
        Review.product_id == product_id,
        Review.created_at >= thirty_days_ago
    ).count()
    
    return ReviewStatsResponse(
        total_reviews=total_reviews,
        average_rating=round(avg_rating, 2),
        rating_distribution=rating_distribution,
        verified_reviews_count=verified_count,
        recent_reviews_count=recent_count
    )


async def update_product_rating(product_id: int, db: Session):
    """Обновить рейтинг товара на основе отзывов"""
    
    # Вычисляем новый средний рейтинг
    avg_rating = db.query(func.avg(Review.rating)).filter(Review.product_id == product_id).scalar() or 0.0
    
    # Подсчитываем количество отзывов
    reviews_count = db.query(Review).filter(Review.product_id == product_id).count()
    
    # Обновляем товар
    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        product.rating = round(avg_rating, 2)
        product.reviews_count = reviews_count
        db.commit()
    
    return avg_rating, reviews_count 