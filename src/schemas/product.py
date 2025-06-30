from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from .store import StoreBrief


class ProductBase(BaseModel):
    """Базовая схема товара"""
    name: str
    description: Optional[str] = None
    price: float
    original_price: Optional[float] = None
    category: str
    brand: Optional[str] = None
    sizes: List[str] = []
    colors: List[str] = []
    image_urls: List[str] = []
    stock_quantity: int = 0
    is_active: bool = True

    @validator('price', 'original_price')
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError('Цена не может быть отрицательной')
        return v

    @validator('stock_quantity')
    def validate_stock(cls, v):
        if v < 0:
            raise ValueError('Количество на складе не может быть отрицательным')
        return v


class ProductCreate(ProductBase):
    """Схема для создания товара"""
    store_id: int


class ProductUpdate(BaseModel):
    """Схема для обновления товара"""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    sizes: Optional[List[str]] = None
    colors: Optional[List[str]] = None
    image_urls: Optional[List[str]] = None
    stock_quantity: Optional[int] = None
    is_active: Optional[bool] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None


class PriceInfo(BaseModel):
    """Информация о цене товара"""
    current: float
    original: Optional[float] = None
    discount_percentage: float = 0.0
    has_discount: bool = False


class ProductResponse(ProductBase):
    """Схема ответа с информацией о товаре"""
    id: int
    rating: float
    reviews_count: int
    store: StoreBrief
    price_info: PriceInfo
    discount_percentage: float
    is_in_stock: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_computed(cls, product):
        """Создание схемы из ORM объекта с вычисляемыми полями"""
        data = {
            **product.__dict__,
            'price_info': product.price_display,
            'discount_percentage': product.discount_percentage,
            'is_in_stock': product.is_in_stock,
            'store': product.store
        }
        return cls(**data)


class ProductBrief(BaseModel):
    """Краткая информация о товаре"""
    id: int
    name: str
    price: float
    original_price: Optional[float] = None
    rating: float
    image_urls: List[str]
    discount_percentage: float
    is_in_stock: bool
    store: StoreBrief

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Схема списка товаров"""
    products: List[ProductBrief]
    total: int
    page: int
    per_page: int
    filters: Dict[str, Any] = {}


class ProductSearchQuery(BaseModel):
    """Схема для поиска товаров"""
    query: Optional[str] = None
    category: Optional[str] = None
    city: Optional[str] = None
    store_id: Optional[int] = None
    brand: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rating: Optional[float] = None
    sizes: Optional[List[str]] = None
    colors: Optional[List[str]] = None
    in_stock_only: bool = False
    sort_by: str = "created_at"  # created_at, price, rating, name
    sort_order: str = "desc"  # asc, desc
    page: int = 1
    per_page: int = 20


class CategoryResponse(BaseModel):
    """Схема категории товаров"""
    category: str
    products_count: int
    avg_price: float
    top_brands: List[str]


class CategoriesListResponse(BaseModel):
    """Список категорий"""
    categories: List[CategoryResponse]


class ProductStatsResponse(BaseModel):
    """Статистика товара"""
    id: int
    name: str
    total_views: int = 0
    total_sales: int = 0
    rating_distribution: Dict[int, int] = {}  # {5: 10, 4: 5, 3: 2, 2: 1, 1: 0}
    popular_sizes: List[str] = []
    popular_colors: List[str] = []

    class Config:
        from_attributes = True 