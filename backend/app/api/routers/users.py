"""
User profile router.
Get and update profile, deal statistics,
user lookup by ID.
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db
from app.db.models.deal import Deal, DealStatus
from app.db.models.user import User
from app.db.models.channel import Channel
from app.schemas.user import ProfileOut, ProfileUpdateIn, PublicProfileOut, PublicProfileChannelOut, PublicProfileCampaignOut

router = APIRouter()

def _get_profile_stats(user_id: str, db: Session) -> tuple[float, int, int]:
    owned_channel_ids = [c[0] for c in db.query(Channel.id).filter(Channel.owner_id == user_id).all()]
    total_earned_ton = 0.0
    successful_deals_count = 0
    if owned_channel_ids:
        total_earned_ton = float(db.query(func.sum(Deal.price_ton)).filter(Deal.channel_id.in_(owned_channel_ids), Deal.status == DealStatus.released.value).scalar() or 0.0)
        successful_deals_count = db.query(func.count(Deal.id)).filter(Deal.channel_id.in_(owned_channel_ids), Deal.status == DealStatus.released.value).scalar() or 0
    
    successful_purchases_count = db.query(func.count(Deal.id)).filter(Deal.advertiser_id == user_id, Deal.status == DealStatus.released.value).scalar() or 0
    return total_earned_ton, successful_deals_count, successful_purchases_count

@router.get("/profile", response_model=ProfileOut)
def get_profile(user=CurrentUser, db: Session = Depends(get_db)):
    earned, deals, purchases = _get_profile_stats(user.id, db)
    return ProfileOut(id=user.id, display_name=user.display_name, telegram_username=user.telegram_username, wallet_address=user.wallet_address or "", total_earned_ton=earned, successful_deals_count=deals, successful_purchases_count=purchases)

@router.patch("/profile", response_model=ProfileOut)
def update_profile(payload: ProfileUpdateIn, user=CurrentUser, db: Session = Depends(get_db)):
    wallet_address = (payload.wallet_address or "").strip()
    user.wallet_address = wallet_address
    db.commit()
    db.refresh(user)
    
    earned, deals, purchases = _get_profile_stats(user.id, db)
    return ProfileOut(id=user.id, display_name=user.display_name, telegram_username=user.telegram_username, wallet_address=user.wallet_address or "", total_earned_ton=earned, successful_deals_count=deals, successful_purchases_count=purchases)

@router.get("/{user_id}/public-profile", response_model=PublicProfileOut)
def get_public_profile(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get channels (published only) with ratings
    channels_db = db.query(Channel).filter(Channel.owner_id == user_id, Channel.is_published == True).all()
    channels = [PublicProfileChannelOut(id=ch.id, title=ch.title, handle=ch.handle, rating_avg=ch.rating_avg, rating_count=ch.rating_count) for ch in channels_db]
    
    # Get campaigns with ratings
    from app.db.models.campaign import Campaign, CampaignStatus
    campaigns_db = db.query(Campaign).filter(Campaign.owner_id == user_id, Campaign.status == CampaignStatus.open).all()
    campaigns = [PublicProfileCampaignOut(id=cp.id, title=cp.title, brief=cp.brief, rating_avg=cp.rating_avg, rating_count=cp.rating_count) for cp in campaigns_db]
    
    # Stats
    earned, deals_count, purchases_count = _get_profile_stats(user_id, db)
    
    # Determine role label
    has_channels = len(channels) > 0
    has_campaigns = len(campaigns) > 0
    if has_channels and has_campaigns:
        role_label = "User"
    elif has_campaigns:
        role_label = "Advertiser"
    elif has_channels:
        role_label = "Publisher"
    else:
        role_label = "User"
    
    return PublicProfileOut(
        role_label=role_label,
        rating_advertiser_avg=user.rating_advertiser_avg,
        rating_advertiser_count=user.rating_advertiser_count,
        rating_owner_avg=user.rating_owner_avg,
        rating_owner_count=user.rating_owner_count,
        successful_deals_count=deals_count,
        successful_purchases_count=purchases_count,
        channels=channels,
        campaigns=campaigns,
    )
