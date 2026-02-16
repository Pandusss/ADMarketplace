"""
Authentication router.
/me endpoint — returns the current user data
based on Telegram WebApp initData.
"""
from __future__ import annotations
from fastapi import APIRouter
from app.core.deps import CurrentUser
from app.schemas.user import UserOut

router = APIRouter()

@router.get("/me", response_model=UserOut)
def get_me(user=CurrentUser):
    """Mock auth: returns current user validation data."""
    return user
