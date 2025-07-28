"""
Models package initialization.
Imports all models to ensure they are registered with SQLAlchemy Base.
This file is used by Alembic to discover all models for migrations.
"""

from src.models.user import User
from src.models.clothing import ClothingItem
from src.models.chat import Chat, Message
from src.models.waitlist import WaitListItem
from src.models.tryon import TryOn
from src.models.store import Store
from src.models.product import Product
from src.models.review import Review

__all__ = [
    "User",
    "ClothingItem", 
    "Chat",
    "Message",
    "WaitListItem",
    "TryOn",
    "Store",
    "Product",
    "Review"
] 