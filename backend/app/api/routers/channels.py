"""
Channel management router.
Registration, verification, publishing, settings update,
schedule slot management and campaign offers.
"""
from __future__ import annotations
import httpx
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser, get_db
from app.core.config import settings
from app.db.models.channel import Channel
from app.db.models.channel_verification import ChannelVerification
from app.db.models.user import User
from app.schemas.channel import ChannelAvailabilityIn, ChannelOut, ChannelUpdateIn
from app.db.models.channel_offer import ChannelOffer
from app.schemas.channel_offer import ChannelOfferCreateIn, ChannelOfferOut
from app.infra.telegram.bot_client import TelegramBotClient
from app.infra.telegram.webapp_auth import TelegramWebAppAuthError, validate_init_data
from app.infra.queue.rq import get_queue
from app.domain.scheduling.slots import parse_hhmm

router = APIRouter()

# --- Public Endpoints ---

@router.get("", response_model=list[ChannelOut])
def list_channels(db: Session = Depends(get_db)):
    """Public Feed: only verified AND published channels are visible"""
    return db.query(Channel).filter(Channel.is_verified == True, Channel.is_published == True).all()

@router.get("/add-bot-url")
def get_add_bot_url():
    if not settings.telegram_bot_username:
        raise HTTPException(status_code=500, detail="BOT username not configured")
    add_bot_url = f"https://t.me/{settings.telegram_bot_username}?startchannel=&admin={settings.telegram_admin_permissions}"
    return {"add_bot_url": add_bot_url}

@router.get("/{id}", response_model=ChannelOut)
def get_channel(id: str, db: Session = Depends(get_db)):
    c = db.query(Channel).filter(Channel.id == id).one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Channel not found")
    return c

# --- User Channel Management ---

@router.get("/my/list", response_model=list[ChannelOut])
def list_my_channels(user=CurrentUser, db: Session = Depends(get_db)):
    return db.query(Channel).filter(Channel.owner_id == user.id, Channel.is_verified == True).all()

@router.post("/{id}/rescan", response_model=ChannelOut)
def rescan_channel(id: str, db: Session = Depends(get_db), user=CurrentUser):
    channel = db.query(Channel).filter(Channel.id == id).one_or_none()
    if not channel: raise HTTPException(status_code=404)
    if channel.owner_id != user.id: raise HTTPException(status_code=403)
    
    queue = get_queue()
    queue.enqueue("app.tasks.analytics_tasks.update_channel_analytics", channel.id)
    return channel

@router.post("/{id}/publish", response_model=ChannelOut)
def publish_channel(id: str, db: Session = Depends(get_db), user=CurrentUser):
    channel = db.query(Channel).filter(Channel.id == id).one_or_none()
    if not channel: raise HTTPException(status_code=404)
    if channel.owner_id != user.id: raise HTTPException(status_code=403)
    if not channel.is_verified: raise HTTPException(status_code=409, detail="Not verified")
    
    if not user.wallet_address:
        raise HTTPException(status_code=409, detail="Wallet address is required to publish a channel and receive payouts.")
    
    channel.is_published = 1
    db.commit()
    return channel

@router.post("/{id}/unpublish", response_model=ChannelOut)
def unpublish_channel(id: str, db: Session = Depends(get_db), user=CurrentUser):
    channel = db.query(Channel).filter(Channel.id == id).one_or_none()
    if not channel: raise HTTPException(status_code=404)
    if channel.owner_id != user.id: raise HTTPException(status_code=403)
    
    channel.is_published = 0
    db.commit()
    return channel

@router.patch("/{id}/availability", response_model=ChannelOut)
def update_channel_availability(id: str, payload: ChannelAvailabilityIn, user=CurrentUser, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == id).one_or_none()
    if not channel: raise HTTPException(status_code=404)
    if channel.owner_id != user.id: raise HTTPException(status_code=403)

    tz = (payload.posting_timezone or "UTC").strip()
    try: ZoneInfo(tz)
    except: raise HTTPException(status_code=422, detail="Invalid timezone")

    try:
        sh, sm = parse_hhmm(payload.posting_window_start)
        eh, em = parse_hhmm(payload.posting_window_end)
    except: raise HTTPException(status_code=422, detail="Invalid time")

    if (eh, em) <= (sh, sm): raise HTTPException(status_code=422)

    channel.posting_timezone = tz
    channel.posting_window_start = f"{sh:02d}:{sm:02d}"
    channel.posting_window_end = f"{eh:02d}:{em:02d}"
    channel.posting_slot_minutes = int(payload.posting_slot_minutes or 30)
    db.commit()
    return channel

@router.patch("/{id}", response_model=ChannelOut)
def update_channel_metadata(id: str, payload: ChannelUpdateIn, user=CurrentUser, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == id).one_or_none()
    if not channel: raise HTTPException(status_code=404)
    if channel.owner_id != user.id: raise HTTPException(status_code=403)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(channel, field, value)
    db.commit()
    return channel

@router.get("/{id}/avatar")
async def get_channel_avatar(id: str, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == id).one_or_none()
    if not channel: raise HTTPException(status_code=404)

    file_id = getattr(channel, "avatar_file_id", None)
    bot = TelegramBotClient(settings.telegram_bot_token)
    if not file_id:
        chat_id_tg = channel.telegram_channel_id or (f"@{channel.handle}" if channel.handle else None)
        if not chat_id_tg: raise HTTPException(status_code=404)
        try:
            chat_info = await bot.get_chat(str(chat_id_tg))
            photo = chat_info.get("photo")
            if photo:
                file_id = photo.get("small_file_id") or photo.get("big_file_id")
                if file_id:
                    channel.avatar_file_id = file_id
                    db.commit()
        except: pass

    if not file_id: raise HTTPException(status_code=404)
    file_info = await bot.get_file(file_id)
    file_path = file_info.get("file_path")
    if not file_path: raise HTTPException(status_code=404)
    
    tg_url = f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{file_path}"
    async def stream_file():
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", tg_url) as r:
                async for chunk in r.aiter_bytes(): yield chunk

    return StreamingResponse(stream_file(), media_type="image/jpeg")

@router.post("/{id}/offer", response_model=ChannelOfferOut)
def create_channel_offer(id: str, payload: ChannelOfferCreateIn, user=CurrentUser, db: Session = Depends(get_db)):
    channel = db.query(Channel).filter(Channel.id == id).one_or_none()
    if not channel: raise HTTPException(status_code=404)
    if channel.owner_id == user.id: raise HTTPException(status_code=403, detail="Cannot offer to own channel")

    offer = ChannelOffer(
        id=f"co_{uuid4().hex[:8]}",
        channel_id=channel.id,
        advertiser_id=user.id,
        applicant_id=user.id,
        offer_price_ton=channel.price_per_post_ton,
        message=payload.message,
        campaign_brief=payload.campaign_brief,
        campaign_title=payload.campaign_title,
        creative_mode=payload.creative_mode,
        creative_instructions=payload.creative_instructions,
        template_id=payload.template_id,
        preferred_publish_at=payload.preferred_publish_at,
        post_duration_hours=payload.post_duration_hours,
        status="pending"
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer

# --- Verification Logic (Legacy Paths maintained for compatibility) ---

class ChannelInitIn(BaseModel):
    initData: str = Field(default="")
    token: str | None = None

class ChannelInitOut(BaseModel):
    token: str
    bot_username: str
    add_bot_url: str

class ChannelStatusIn(BaseModel):
    initData: str = Field(default="")
    token: str

class ChannelStatusOut(BaseModel):
    verified: bool
    status: str
    channel_id: str | None = None
    channel_username: str | None = None
    channel_title: str | None = None

@router.post("/verification/init", response_model=ChannelInitOut)
def init_channel_verification(payload: ChannelInitIn, db: Session = Depends(get_db)):
    try: tg_user = validate_init_data(payload.initData, settings.telegram_bot_token)
    except Exception: raise HTTPException(status_code=401)

    user = db.query(User).filter(User.telegram_user_id == tg_user.id).one_or_none()
    if not user:
        user = User(id=f"tg_{tg_user.id}", display_name=tg_user.first_name or "User", telegram_user_id=tg_user.id)
        db.add(user)
        db.flush()

    token = payload.token or uuid4().hex
    ver = ChannelVerification(user_id=user.id, telegram_user_id=tg_user.id, token=token, verified=0)
    db.add(ver)
    db.commit()

    add_bot_url = f"https://t.me/{settings.telegram_bot_username}?startchannel=channel_{token}&admin={settings.telegram_admin_permissions}"
    return {"token": token, "bot_username": settings.telegram_bot_username or "", "add_bot_url": add_bot_url}

@router.post("/verification/status", response_model=ChannelStatusOut)
def get_channel_verification_status(payload: ChannelStatusIn, db: Session = Depends(get_db)):
    try: tg_user = validate_init_data(payload.initData, settings.telegram_bot_token)
    except Exception: raise HTTPException(status_code=401)

    ver = db.query(ChannelVerification).filter(ChannelVerification.token == payload.token).one_or_none()
    if not ver or ver.telegram_user_id != tg_user.id: raise HTTPException(status_code=404)

    if ver.verified:
        return {"verified": True, "status": "verified", "channel_id": ver.telegram_channel_id, "channel_username": ver.channel_username, "channel_title": ver.channel_title}
    return {"verified": False, "status": "pending"}

@router.post("/verification/complete")
def complete_channel_setup(payload: dict, db: Session = Depends(get_db)):
    # Payload needs special handling or pydantic model
    try: tg_user = validate_init_data(payload.get("initData", ""), settings.telegram_bot_token)
    except Exception: raise HTTPException(status_code=401)

    ver = db.query(ChannelVerification).filter(ChannelVerification.token == payload.get("token")).one_or_none()
    if not ver or not ver.verified: raise HTTPException(status_code=409)

    channel = db.query(Channel).filter(Channel.telegram_channel_id == ver.telegram_channel_id).one_or_none()
    if not channel: raise HTTPException(status_code=404)

    channel.owner_id = f"tg_{tg_user.id}"
    channel.category = payload.get("category", "Crypto")
    channel.language = payload.get("language", "EN")
    channel.price_per_post_ton = float(payload.get("pricePerPostTON", 0.0))
    channel.price_top_hour_ton = float(payload.get("priceTopHourTON", 0.0))
    channel.top_price_step_pct = float(payload.get("topPriceStepPct", 0.0))
    channel.description = payload.get("description", "")
    channel.wallet_address = payload.get("walletAddress", "")
    db.commit()
    return {"ok": True}
