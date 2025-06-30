from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, JSON, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base


class Product(Base):
    """Модель товара"""
    
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False, index=True)
    original_price = Column(Float, nullable=True)  # Для отображения скидок
    
    # Характеристики товара
    sizes = Column(JSON, default=list)  # ["XS", "S", "M", "L", "XL"]
    colors = Column(JSON, default=list)  # ["white", "black", "red"]
    image_urls = Column(JSON, default=list)  # Массив URL изображений
    
    # Категоризация
    category = Column(String(50), nullable=False, index=True)
    brand = Column(String(100), nullable=True, index=True)
    
    # Рейтинг и отзывы
    rating = Column(Float, default=0.0)  # Средний рейтинг товара
    reviews_count = Column(Integer, default=0)
    
    # Инвентарь
    stock_quantity = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)
    
    # Векторизация для поиска
    vector_embedding = Column(JSON, nullable=True)  # Векторное представление для семантического поиска
    
    # Связи
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    store = relationship("Store", back_populates="products")
    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")

    @property
    def discount_percentage(self) -> float:
        """Процент скидки"""
        if self.original_price and self.original_price > self.price:
            return round(((self.original_price - self.price) / self.original_price) * 100, 1)
        return 0.0

    @property
    def is_in_stock(self) -> bool:
        """Есть ли товар в наличии"""
        return self.stock_quantity > 0

    @property
    def price_display(self) -> dict:
        """Отформатированная информация о цене"""
        return {
            "current": self.price,
            "original": self.original_price,
            "discount_percentage": self.discount_percentage,
            "has_discount": self.discount_percentage > 0
        } 