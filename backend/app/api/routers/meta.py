"""
System metadata router.
Returns public configuration parameters
(Telegram bot username, etc.) for the frontend.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("")
def get_meta() -> dict:
    return {
        "telegram_bot_username": settings.telegram_bot_username,
    }
