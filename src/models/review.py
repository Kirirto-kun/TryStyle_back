from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base


class Review(Base):
    """Модель отзыва на товар"""
    
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    rating = Column(Integer, nullable=False)  # Оценка от 1 до 5
    comment = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=False)  # Проверенный отзыв
    
    # Связи
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    product = relationship("Product", back_populates="reviews")
    user = relationship("User", back_populates="reviews")

    @property
    def rating_stars(self) -> str:
        """Отображение рейтинга звездочками"""
        return "⭐" * self.rating + "☆" * (5 - self.rating)

    def __repr__(self):
        return f"<Review(id={self.id}, rating={self.rating}, product_id={self.product_id})>" 