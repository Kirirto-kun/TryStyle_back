from pydantic import BaseModel, validator, Field
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
        """Критически низкий остаток (менее 3)"""
        return self.current_stock < 3
    
    @property
    def is_warning(self) -> bool:
        """Предупреждение о низком остатке"""
        return self.current_stock <= self.threshold


class PhotoProductUpload(BaseModel):
    """Создание товара через загрузку фотографий"""
    images_base64: List[str] = Field(
        ..., 
        min_items=1, 
        max_items=5,
        description="Массив base64 изображений (от 1 до 5 фото)"
    )
    name: Optional[str] = Field(
        None,
        max_length=200,
        description="Название товара (опционально - если не указано, будет сгенерировано GPT)"
    )
    price: float = Field(
        ...,
        gt=0,
        description="Цена товара в тенге"
    )
    original_price: Optional[float] = Field(
        None,
        gt=0,
        description="Первоначальная цена до скидки (опционально)"
    )
    sizes: List[str] = Field(
        default_factory=list,
        description="Доступные размеры"
    )
    colors: List[str] = Field(
        default_factory=list,
        description="Доступные цвета"
    )
    stock_quantity: int = Field(
        default=0,
        ge=0,
        description="Количество на складе"
    )
    
    @validator('images_base64')
    def validate_images(cls, v):
        for img in v:
            if not img.startswith('data:image/'):
                raise ValueError('Каждое изображение должно быть в формате base64 data URL')
        return v
    
    @validator('original_price')
    def validate_original_price(cls, v, values):
        if v is not None and 'price' in values and v <= values['price']:
            raise ValueError('Первоначальная цена должна быть больше текущей цены')
        return v 