"""
User Schemas.
Pydantic models for user profiles, authentication data, 
and public-facing account statistics.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    wallet_address: str = ""


class ProfileOut(BaseModel):
    """User profile with statistics."""
    
    id: str
    display_name: str
    telegram_username: str | None = None
    wallet_address: str = ""
    total_earned_ton: float = 0.0
    successful_deals_count: int = 0
    successful_purchases_count: int = 0
    rating_avg: float = 0.0
    rating_count: int = 0
    
    rating_advertiser_avg: float = 0.0
    rating_advertiser_count: int = 0
    rating_owner_avg: float = 0.0
    rating_owner_count: int = 0


class ProfileUpdateIn(BaseModel):
    """Update profile fields."""
    
    wallet_address: str = Field(default="", max_length=100)


class PublicProfileChannelOut(BaseModel):
    id: str
    title: str
    handle: str
    rating_avg: float = 0.0
    rating_count: int = 0


class PublicProfileCampaignOut(BaseModel):
    id: str
    title: str
    brief: str
    rating_avg: float = 0.0
    rating_count: int = 0


class PublicProfileOut(BaseModel):
    """Anonymous public profile — no real name, no username."""
    role_label: str  # "Advertiser" or "Publisher" or "User"
    rating_advertiser_avg: float = 0.0
    rating_advertiser_count: int = 0
    rating_owner_avg: float = 0.0
    rating_owner_count: int = 0
    successful_deals_count: int = 0
    successful_purchases_count: int = 0
    channels: list[PublicProfileChannelOut] = []
    campaigns: list[PublicProfileCampaignOut] = []
