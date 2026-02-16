"""
FastAPI Dependencies.
Provides reusable dependency injectors for authentication, 
database sessions, and background task clients.
"""
from __future__ import annotations
from collections.abc import Generator
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.user import User
from app.core.config import settings
from app.infra.telegram.webapp_auth import TelegramWebAppAuthError, validate_init_data

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    db: Session = Depends(get_db),
    x_tg_init_data: str | None = Header(default=None, alias="X-Tg-Init-Data"),
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> User:
    init_data = (x_tg_init_data or x_telegram_init_data or "").strip()
    if not init_data:
        raise HTTPException(status_code=401, detail="Missing Telegram initData")

    try:
        tg_user = validate_init_data(init_data, settings.telegram_bot_token)
    except TelegramWebAppAuthError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    user = db.query(User).filter(User.telegram_user_id == tg_user.id).one_or_none()
    if not user:
        display = tg_user.first_name or tg_user.username or "Telegram user"
        user = User(
            id=f"tg_{tg_user.id}",
            display_name=display,
            telegram_user_id=tg_user.id,
            telegram_username=tg_user.username,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user

CurrentUser = Depends(get_current_user)
