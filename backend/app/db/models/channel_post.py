from __future__ import annotations
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.models.base import Base

class ChannelPost(Base):
    __tablename__ = "channel_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    channel_id: Mapped[str] = mapped_column(String, ForeignKey("channels.id"), nullable=False, index=True)
    post_id: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    forwards: Mapped[int] = mapped_column(Integer, default=0)
    replies: Mapped[int] = mapped_column(Integer, default=0)
    reactions: Mapped[str] = mapped_column(Text, default="{}") 
    content_type: Mapped[str] = mapped_column(String, default="other")
    has_links: Mapped[bool] = mapped_column(Boolean, default=False)
    grouped_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    channel: Mapped["Channel"] = relationship("Channel")
