"""
User Database Model.
ORM representation of application users, including their 
Telegram identities, wallet addresses, and rating metrics.
"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.models.base import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, unique=True)
    telegram_username: Mapped[str | None] = mapped_column(String, nullable=True)
    wallet_address: Mapped[str] = mapped_column(String, nullable=False, default="")
    
    # Advertiser rating (reviews from channel owners)
    rating_advertiser_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rating_advertiser_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Channel owner rating (reviews from advertisers)
    rating_owner_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rating_owner_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Legacy field (keep for now to avoid breaking existing code before migration)
    rating_avg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
