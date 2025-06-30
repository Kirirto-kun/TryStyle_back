from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base


class Store(Base):
    """Модель магазина"""
    
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    city = Column(String(50), nullable=False, index=True)  # Город магазина
    logo_url = Column(String(500), nullable=True)
    website_url = Column(String(500), nullable=True)
    rating = Column(Float, default=0.0)  # Средний рейтинг магазина
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    products = relationship("Product", back_populates="store", cascade="all, delete-orphan")

    @property
    def total_products(self) -> int:
        """Количество товаров в магазине"""
        return len(self.products) if self.products else 0 