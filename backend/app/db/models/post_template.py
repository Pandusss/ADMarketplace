from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.models.base import Base

class PostTemplate(Base):
    __tablename__ = "post_templates"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False, default="")
    creative_chat_id: Mapped[str | None] = mapped_column(String, nullable=True)
    creative_message_ids: Mapped[str | None] = mapped_column(String, nullable=True)
    creative_type: Mapped[str | None] = mapped_column(String, nullable=True)
    preview_text: Mapped[str] = mapped_column(String, nullable=False, default="")
    preview_file_id: Mapped[str] = mapped_column(String, nullable=False, default="")
    preview_file_ids: Mapped[str] = mapped_column(String, nullable=False, default="")
    preview_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    waiting_for_content: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
