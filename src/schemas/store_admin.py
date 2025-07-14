from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from .user import UserResponse
from .store import StoreBrief
from .product import ProductBrief


class StoreAdminDashboard(BaseModel):
    """Дашборд админа магазина"""
    store: StoreBrief
    total_products: int
    active_products: int
    inactive_products: int
    products_by_category: Dict[str, int]
    total_reviews: int
    average_rating: float
    recent_products: List[ProductBrief]
    low_stock_products: List[ProductBrief]  # Товары с низким остатком
    top_rated_products: List[ProductBrief]


class StoreProductStats(BaseModel):
    """Статистика товаров магазина"""
    total_products: int
    active_products: int
    inactive_products: int
    out_of_stock_products: int
    products_by_category: Dict[str, int]
    average_price: float
    price_range: Dict[str, float]  # min, max
    average_rating: float
    total_reviews: int


class StoreAdminUserCreate(BaseModel):
    """Создание админа магазина"""
    email: str
    username: str
    password: str
    store_id: int
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v


class StoreAdminUserResponse(UserResponse):
    """Ответ с информацией об админе магазина"""
    role: str
    store_id: Optional[int]
    managed_store: Optional[StoreBrief]


class StoreAdminSettings(BaseModel):
    """Настройки магазина"""
    name: str
    description: Optional[str] = None
    city: str
    logo_url: Optional[str] = None
    website_url: Optional[str] = None


class StoreAnalytics(BaseModel):
    """Аналитика магазина"""
    period: str  # "week", "month", "year"
    products_added: int
    reviews_received: int
    average_rating_change: float
    popular_categories: List[Dict[str, Any]]
    rating_distribution: Dict[str, int]  # 1-5 stars distribution


class StoreAdminProductCreate(BaseModel):
    """Создание товара админом магазина (store_id автоматически берется из пользователя)"""
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


class StoreAdminProductUpdate(BaseModel):
    """Обновление товара админом магазина"""
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

    @validator('price', 'original_price')
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError('Цена не может быть отрицательной')
        return v

    @validator('stock_quantity')
    def validate_stock(cls, v):
        if v is not None and v < 0:
            raise ValueError('Количество на складе не может быть отрицательным')
        return v


class StoreAdminListResponse(BaseModel):
    """Список админов магазинов"""
    store_admins: List[StoreAdminUserResponse]
    total: int
    page: int
    per_page: int


class LowStockAlert(BaseModel):
    """Уведомление о низком остатке"""
    product_id: int
    product_name: str
    current_stock: int
    threshold: int = 5  # Порог для уведомления
    category: str
    
    @property
    def is_critical(self) -> bool:
        """Критически низкий остаток (0-1 шт)"""
        return self.current_stock <= 1
    
    @property
    def is_warning(self) -> bool:
        """Предупреждение (2-5 шт)"""
        return 2 <= self.current_stock <= 5 