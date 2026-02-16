"""
Channel offer router.
Channel offer listing, offer creation/acceptance by advertiser,
automatic deal creation and Telegram notifications.
"""
from __future__ import annotations
from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db
from app.db.models.channel import Channel
from app.db.models.channel_offer import ChannelOffer
from app.db.models.deal import Deal, DealStatus, get_random_deal_emoji
from app.db.models.post_template import PostTemplate
from app.db.models.user import User
from app.schemas.channel import ChannelOut
from app.schemas.channel_offer import ChannelOfferOut, ChannelOfferListOut, ChannelOfferDetailOut
from app.schemas.deal import DealOut
from app.domain.chat.service import ChatService
from app.infra.telegram.bot_client import TelegramBotClient
from app.core.config import settings

router = APIRouter()

def _now() -> datetime: return datetime.utcnow()


@router.get("/my", response_model=list[ChannelOfferListOut])
def list_my_channel_offers(user=CurrentUser, db: Session = Depends(get_db)):
    rows = (
        db.query(ChannelOffer, Channel.title, Channel.handle, Deal.status)
        .join(Channel, Channel.id == ChannelOffer.channel_id)
        .outerjoin(Deal, Deal.id == ChannelOffer.deal_id)
        .filter(ChannelOffer.advertiser_id == user.id)
        .order_by(ChannelOffer.created_at.desc())
        .all()
    )
    result = []
    for offer, title, handle, deal_status in rows:
        channel_name = title or (f"@{handle}" if handle else "") or offer.channel_id
        result.append(
            ChannelOfferListOut(
                **ChannelOfferOut.model_validate(offer).model_dump(),
                channel_name=channel_name,
                deal_status=deal_status,
            )
        )
    return result


@router.get("/incoming", response_model=list[ChannelOfferListOut])
def list_incoming_channel_offers(user=CurrentUser, db: Session = Depends(get_db)):
    rows = (
        db.query(ChannelOffer, Channel.title, Channel.handle, Deal.status)
        .join(Channel, Channel.id == ChannelOffer.channel_id)
        .outerjoin(Deal, Deal.id == ChannelOffer.deal_id)
        .filter(Channel.owner_id == user.id)
        .order_by(ChannelOffer.created_at.desc())
        .all()
    )
    result = []
    for offer, title, handle, deal_status in rows:
        channel_name = title or (f"@{handle}" if handle else "") or offer.channel_id
        result.append(
            ChannelOfferListOut(
                **ChannelOfferOut.model_validate(offer).model_dump(),
                channel_name=channel_name,
                deal_status=deal_status,
            )
        )
    return result


@router.get("/{id}", response_model=ChannelOfferDetailOut)
def get_channel_offer(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    offer = db.query(ChannelOffer).filter(ChannelOffer.id == id).one_or_none()
    if not offer: raise HTTPException(status_code=404)
    ch = db.query(Channel).filter(Channel.id == offer.channel_id).one_or_none()
    if not ch: raise HTTPException(status_code=404)
    is_owner = ch.owner_id == user.id
    if offer.advertiser_id != user.id and not is_owner: raise HTTPException(status_code=403)
    advertiser = db.query(User).filter(User.id == offer.advertiser_id).one_or_none()
    return ChannelOfferDetailOut(
        id=offer.id,
        channel_id=offer.channel_id,
        advertiser_id=offer.advertiser_id,
        offer_price_ton=float(offer.offer_price_ton or 0.0),
        message=(offer.message or "").strip(),
        status=offer.status,
        deal_id=offer.deal_id,
        created_at=offer.created_at,
        campaign_brief=offer.campaign_brief or "",
        campaign_title=offer.campaign_title or "",
        creative_mode=offer.creative_mode or "template",
        creative_instructions=offer.creative_instructions,
        preferred_publish_at=offer.preferred_publish_at,
        post_duration_hours=offer.post_duration_hours or 24,
        channel=ChannelOut.model_validate(ch),
        viewer_role="incoming" if is_owner else "my",
        can_start_deal=bool(is_owner and offer.status == "pending" and not offer.deal_id),
        advertiser_rating_avg=advertiser.rating_advertiser_avg if advertiser else 0.0,
        advertiser_rating_count=advertiser.rating_advertiser_count if advertiser else 0,
        advertiser_rating_advertiser_avg=advertiser.rating_advertiser_avg if advertiser else 0.0,
        advertiser_rating_advertiser_count=advertiser.rating_advertiser_count if advertiser else 0,
        advertiser_display_name=advertiser.display_name if advertiser else "",
        advertiser_username=advertiser.telegram_username if advertiser else None,
    )


@router.delete("/{id}")
def cancel_channel_offer(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    offer = db.query(ChannelOffer).filter(ChannelOffer.id == id).one_or_none()
    if not offer: raise HTTPException(status_code=404)
    ch = db.query(Channel).filter(Channel.id == offer.channel_id).one_or_none()
    is_owner = ch and ch.owner_id == user.id
    if offer.advertiser_id != user.id and not is_owner: raise HTTPException(status_code=403)
    if offer.deal_id: raise HTTPException(status_code=409, detail="Deal already exists")
    db.delete(offer)
    db.commit()
    return {"ok": True}


@router.post("/{id}/start-deal", response_model=DealOut)
async def start_deal_from_channel_offer(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    offer = db.query(ChannelOffer).filter(ChannelOffer.id == id, ChannelOffer.status == "pending").one_or_none()
    if not offer: raise HTTPException(status_code=404)
    ch = db.query(Channel).filter(Channel.id == offer.channel_id).one_or_none()
    if not ch or ch.owner_id != user.id: raise HTTPException(status_code=403)

    seller = db.query(User).filter(User.id == ch.owner_id).first()
    if not seller or not seller.wallet_address: raise HTTPException(status_code=409, detail="Seller wallet missing")

    d = Deal(
        id=f"d_{uuid4().hex[:8]}",
        channel_id=ch.id,
        advertiser_id=offer.advertiser_id,
        emoji=get_random_deal_emoji(),
        status=DealStatus.negotiation.value,
        price_ton=float(offer.offer_price_ton or 0.0),
        campaign_brief=offer.campaign_brief or "",
        campaign_title=offer.campaign_title or "",
        creative_mode=offer.creative_mode or "template",
        creative_instructions=offer.creative_instructions,
        post_duration_hours=offer.post_duration_hours or 24,
        seller_wallet=seller.wallet_address,
        creative_preview_text="",
        creative_preview_file_id="",
        creative_preview_file_ids="",
        created_at=_now(),
        updated_at=_now(),
    )

    if offer.creative_mode == "template" and offer.template_id:
        tpl = db.query(PostTemplate).filter(PostTemplate.id == offer.template_id).first()
        if tpl:
            d.creative_chat_id = tpl.creative_chat_id
            d.creative_message_ids = tpl.creative_message_ids
            d.creative_type = tpl.creative_type
            d.creative_preview_text = tpl.preview_text or ""
            d.creative_preview_file_id = tpl.preview_file_id or ""
            d.creative_preview_file_ids = tpl.preview_file_ids or ""
            d.creative_preview_count = tpl.preview_count
            d.waiting_for_creative = False

    db.add(d)
    offer.status = "accepted"
    offer.deal_id = d.id
    db.commit()

    if settings.telegram_bot_token:
        try:
            bot = TelegramBotClient(settings.telegram_bot_token)
            cs = ChatService(db)
            title = offer.campaign_title or (offer.campaign_brief or "")[:30]
            await cs.notify_deal_start(bot, d, title=f"Offer “{title}”" if title else None)
        except Exception:
            pass
            
    return DealOut.model_validate(d, context={"channel_name": ch.title or ch.handle or ch.id})
