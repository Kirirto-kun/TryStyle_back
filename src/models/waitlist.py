from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base


class WaitListItem(Base):
    """Stores screenshots added by users that await processing."""

    __tablename__ = "waitlist_items"

    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String, nullable=False)
    try_on_url = Column(String, nullable=True)  # URL of the try-on result image
    status = Column(String, default="pending")  # e.g., pending, processed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="waitlist_items") 