from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from src.database import Base

class ClothingItem(Base):
    __tablename__ = "clothing_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    features = Column(JSON, default={})
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationship with User
    user = relationship("User", back_populates="clothing_items") 