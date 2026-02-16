from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.routers import auth, campaigns, channels, channel_offers, channel_offer_routes, deals, users, templates, meta, ton_webhook, reviews
from app.core.deps import CurrentUser, get_db
from app.db.models.channel import Channel
from app.schemas.channel import ChannelOut
from app.schemas.user import ProfileOut, ProfileUpdateIn

api_router = APIRouter()


@api_router.get("/profile", response_model=ProfileOut, tags=["users"])
def get_profile(user=CurrentUser, db: Session = Depends(get_db)):
    from app.api.routers.users import _get_profile_stats
    earned, deals, purchases = _get_profile_stats(user.id, db)
    return ProfileOut(
        id=user.id, 
        display_name=user.display_name, 
        telegram_username=user.telegram_username, 
        wallet_address=user.wallet_address or "", 
        total_earned_ton=earned, 
        successful_deals_count=deals, 
        successful_purchases_count=purchases, 
        rating_avg=user.rating_avg, 
        rating_count=user.rating_count,
        rating_advertiser_avg=user.rating_advertiser_avg,
        rating_advertiser_count=user.rating_advertiser_count,
        rating_owner_avg=user.rating_owner_avg,
        rating_owner_count=user.rating_owner_count
    )


@api_router.patch("/profile", response_model=ProfileOut, tags=["users"])
def update_profile(payload: ProfileUpdateIn, user=CurrentUser, db: Session = Depends(get_db)):
    from app.api.routers.users import _get_profile_stats
    wallet_address = (payload.wallet_address or "").strip()
    user.wallet_address = wallet_address
    db.commit()
    db.refresh(user)
    earned, deals_count, purchases = _get_profile_stats(user.id, db)
    return ProfileOut(
        id=user.id, 
        display_name=user.display_name, 
        telegram_username=user.telegram_username, 
        wallet_address=user.wallet_address or "", 
        total_earned_ton=earned, 
        successful_deals_count=deals_count, 
        successful_purchases_count=purchases, 
        rating_avg=user.rating_avg, 
        rating_count=user.rating_count,
        rating_advertiser_avg=user.rating_advertiser_avg,
        rating_advertiser_count=user.rating_advertiser_count,
        rating_owner_avg=user.rating_owner_avg,
        rating_owner_count=user.rating_owner_count
    )


@api_router.get("/my/channels", response_model=list[ChannelOut], tags=["channels"])
def list_my_channels(user=CurrentUser, db: Session = Depends(get_db)):
    return db.query(Channel).filter(Channel.owner_id == user.id, Channel.is_verified == True).all()


api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(meta.router, prefix="/meta", tags=["meta"])
api_router.include_router(channels.router, prefix="/channels", tags=["channels"])
api_router.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(channel_offers.router, prefix="/campaign-offers", tags=["campaign-offers"])
api_router.include_router(channel_offer_routes.router, prefix="/channel-offers", tags=["channel-offers"])
api_router.include_router(deals.router, prefix="/deals", tags=["deals"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(ton_webhook.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(reviews.router, tags=["reviews"])
