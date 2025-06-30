from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime


class ReviewBase(BaseModel):
    """Базовая схема отзыва"""
    rating: int
    comment: Optional[str] = None

    @validator('rating')
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Рейтинг должен быть от 1 до 5')
        return v


class ReviewCreate(ReviewBase):
    """Схема для создания отзыва"""
    product_id: int


class ReviewUpdate(BaseModel):
    """Схема для обновления отзыва"""
    rating: Optional[int] = None
    comment: Optional[str] = None

    @validator('rating')
    def validate_rating(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError('Рейтинг должен быть от 1 до 5')
        return v


class UserBrief(BaseModel):
    """Краткая информация о пользователе"""
    id: int
    username: str

    class Config:
        from_attributes = True


class ReviewResponse(ReviewBase):
    """Схема ответа с информацией об отзыве"""
    id: int
    product_id: int
    user: UserBrief
    is_verified: bool
    rating_stars: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReviewListResponse(BaseModel):
    """Схема списка отзывов"""
    reviews: List[ReviewResponse]
    total: int
    page: int
    per_page: int
    average_rating: float
    rating_distribution: dict  # {5: 10, 4: 5, 3: 2, 2: 1, 1: 0}


class ReviewStatsResponse(BaseModel):
    """Статистика отзывов"""
    total_reviews: int
    average_rating: float
    rating_distribution: dict
    verified_reviews_count: int
    recent_reviews_count: int  # за последние 30 дней 