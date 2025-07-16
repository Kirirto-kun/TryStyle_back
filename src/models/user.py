from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base
import enum


class UserRole(enum.Enum):
    """Роли пользователей в системе"""
    USER = "user"
    STORE_ADMIN = "store_admin"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    
    # Система ролей
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Новое поле для демонстрации миграций
    phone = Column(String(20), nullable=True)

    # Relationship with ClothingItem
    clothing_items = relationship("ClothingItem", back_populates="user")

    # Relationship with WaitListItem
    waitlist_items = relationship("WaitListItem", back_populates="user")
    
    # Relationship with Chat
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    
    # Relationship with Review
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan") 
    
    # Relationship with Store (для админов магазинов)
    managed_store = relationship("Store", foreign_keys=[store_id], post_update=True)

    @property
    def is_store_admin(self) -> bool:
        """Проверяет, является ли пользователь админом магазина"""
        return self.role == UserRole.STORE_ADMIN

    @property
    def is_admin(self) -> bool:
        """Проверяет, является ли пользователь суперадмином"""
        return self.role == UserRole.ADMIN

    @property
    def can_manage_stores(self) -> bool:
        """Проверяет, может ли пользователь управлять магазинами"""
        return self.role in [UserRole.STORE_ADMIN, UserRole.ADMIN] 