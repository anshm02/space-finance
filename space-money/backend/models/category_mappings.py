"""
SQLAlchemy model for app_category_mappings table.

Maps Lean Technologies transaction categories to the app's
fixed/flexible/savings budget framework.
"""
from sqlalchemy import Column, String, SmallInteger, Boolean, ForeignKey, CheckConstraint, UUID
from sqlalchemy.orm import relationship
from database import Base


class CategoryMapping(Base):
    """
    Category mappings table for user-customizable category display settings.
    
    Maps Lean API categories to user-friendly display names and budget buckets.
    System defaults have user_id = NULL, user customizations have user_id set.
    """
    __tablename__ = "app_category_mappings"
    __table_args__ = (
        CheckConstraint("bucket IN ('fixed', 'flexible', 'savings')", name='ck_bucket_values'),
    )
    
    id = Column(UUID, primary_key=True, server_default="uuid_generate_v4()")
    user_id = Column(UUID, ForeignKey("user.user_profiles.user_id", ondelete="CASCADE"), nullable=True)
    lean_category = Column(String(50), nullable=False)
    display_name = Column(String(50), nullable=False)
    bucket = Column(String(20), nullable=False)
    display_order = Column(SmallInteger, nullable=False, server_default="0")
    is_income = Column(Boolean, nullable=False, server_default="false")
    exclude_from_expenses = Column(Boolean, nullable=False, server_default="false")
    
    # Relationships
    user = relationship("UserProfile", foreign_keys=[user_id])
