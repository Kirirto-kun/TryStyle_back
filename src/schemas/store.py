from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime


class StoreBase(BaseModel):
    """Базовая схема магазина"""
    name: str
    description: Optional[str] = None
    city: str
    logo_url: Optional[str] = None
    website_url: Optional[str] = None


class StoreCreate(StoreBase):
    """Схема для создания магазина"""
    pass


class StoreUpdate(BaseModel):
    """Схема для обновления магазина"""
    name: Optional[str] = None
    description: Optional[str] = None
    city: Optional[str] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    rating: Optional[float] = None


class StoreResponse(StoreBase):
    """Схема ответа с информацией о магазине"""
    id: int
    rating: float
    total_products: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StoreListResponse(BaseModel):
    """Схема списка магазинов"""
    stores: List[StoreResponse]
    total: int
    page: int
    per_page: int


class StoreBrief(BaseModel):
    """Краткая информация о магазине"""
    id: int
    name: str
    city: str
    logo_url: Optional[str] = None
    rating: float

    class Config:
        from_attributes = True


class CityStatsResponse(BaseModel):
    """Статистика по городу"""
    city: str
    stores_count: int
    products_count: int


class CitiesListResponse(BaseModel):
    """Список городов с магазинами"""
    cities: List[CityStatsResponse]


class StoreStatsResponse(BaseModel):
    """Статистика магазина"""
    id: int
    name: str
    city: str
    total_products: int
    active_products: int
    average_rating: float
    total_reviews: int
    categories_count: int
    top_categories: List[str]

    class Config:
        from_attributes = True 