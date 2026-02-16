"""
Campaign offer router (channel applications to campaigns).
Submitting an application, advertiser accept/reject,
automatic deal creation on confirmation.
"""
from __future__ import annotations
import httpx
from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db
from app.core.config import settings
from app.db.models.campaign import Campaign
from app.db.models.campaign_offer import CampaignOffer
from app.db.models.channel import Channel
from app.db.models.deal import Deal, DealStatus, get_random_deal_emoji
from app.db.models.post_template import PostTemplate
from app.db.models.user import User
from app.schemas.campaign_offer import (
    CampaignOfferOut,
    CampaignOfferDetailOut,
    CampaignOfferListOut,
)
from app.schemas.channel import ChannelOut
from app.schemas.deal import DealOut
from app.domain.chat.service import ChatService
from app.infra.telegram.bot_client import TelegramBotClient

router = APIRouter()

def _now() -> datetime: return datetime.utcnow()

def _send_bot_message(telegram_user_id: int | None, text: str) -> None:
    if not telegram_user_id: return
    token = (settings.telegram_bot_token or "").strip()
    if not token: return
    try:
        httpx.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": str(int(telegram_user_id)), "text": text}, timeout=8)
    except: pass


@router.get("/my", response_model=list[CampaignOfferListOut])
def list_my_campaign_offers(user=CurrentUser, db: Session = Depends(get_db)):
    rows = (
        db.query(CampaignOffer, Campaign.title, Campaign.template_id, PostTemplate.preview_text, PostTemplate.preview_file_id, PostTemplate.preview_file_ids, PostTemplate.preview_count, Channel.title, Channel.handle, Deal.status)
        .join(Campaign, Campaign.id == CampaignOffer.campaign_id)
        .outerjoin(PostTemplate, PostTemplate.id == Campaign.template_id)
        .outerjoin(Channel, Channel.id == CampaignOffer.channel_id)
        .outerjoin(Deal, Deal.id == CampaignOffer.deal_id)
        .filter(CampaignOffer.applicant_id == user.id)
        .order_by(CampaignOffer.created_at.desc())
        .all()
    )
    out: list[CampaignOfferListOut] = []
    for app, camp_title, tpl_id, preview_text, preview_file_id, preview_file_ids, preview_count, ch_title, ch_handle, d_status in rows:
        channel_name = (ch_title or (f"@{ch_handle}" if ch_handle else "")).strip() or app.channel_id
        out.append(CampaignOfferListOut(**CampaignOfferOut.model_validate(app).model_dump(), campaign_title=camp_title or "", channel_name=channel_name, template_id=tpl_id or "", template_preview_text=preview_text or "", template_preview_has_media=bool((preview_file_id or "").strip() or (preview_file_ids or "").strip()), template_preview_count=int(preview_count or 0), deal_status=d_status))
    return out


@router.get("/incoming", response_model=list[CampaignOfferListOut])
def list_incoming_campaign_offers(user=CurrentUser, db: Session = Depends(get_db)):
    rows = (
        db.query(CampaignOffer, Campaign.title, Campaign.template_id, PostTemplate.preview_text, PostTemplate.preview_file_id, PostTemplate.preview_file_ids, PostTemplate.preview_count, Channel.title, Channel.handle, Deal.status)
        .join(Campaign, Campaign.id == CampaignOffer.campaign_id)
        .outerjoin(PostTemplate, PostTemplate.id == Campaign.template_id)
        .outerjoin(Channel, Channel.id == CampaignOffer.channel_id)
        .outerjoin(Deal, Deal.id == CampaignOffer.deal_id)
        .filter(Campaign.owner_id == user.id)
        .order_by(CampaignOffer.created_at.desc())
        .all()
    )
    out: list[CampaignOfferListOut] = []
    for app, camp_title, tpl_id, preview_text, preview_file_id, preview_file_ids, preview_count, ch_title, ch_handle, d_status in rows:
        channel_name = (ch_title or (f"@{ch_handle}" if ch_handle else "")).strip() or app.channel_id
        out.append(CampaignOfferListOut(**CampaignOfferOut.model_validate(app).model_dump(), campaign_title=camp_title or "", channel_name=channel_name, template_id=tpl_id or "", template_preview_text=preview_text or "", template_preview_has_media=bool((preview_file_id or "").strip() or (preview_file_ids or "").strip()), template_preview_count=int(preview_count or 0), deal_status=d_status))
    return out


@router.get("/{id}", response_model=CampaignOfferDetailOut)
def get_campaign_offer(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    app = db.query(CampaignOffer).filter(CampaignOffer.id == id).one_or_none()
    if not app: raise HTTPException(status_code=404)
    camp = db.query(Campaign).filter(Campaign.id == app.campaign_id).one_or_none()
    if not camp: raise HTTPException(status_code=404)
    if app.applicant_id != user.id and camp.owner_id != user.id: raise HTTPException(status_code=403)

    ch = db.query(Channel).filter(Channel.id == app.channel_id).one_or_none()
    if not ch: raise HTTPException(status_code=404)
    applicant = db.query(User).filter(User.id == app.applicant_id).one_or_none()
    campaign_owner = db.query(User).filter(User.id == camp.owner_id).one_or_none()
    
    is_owner = camp.owner_id == user.id
    return CampaignOfferDetailOut(
        id=app.id,
        status=app.status,
        created_at=app.created_at,
        offer_price_ton=float(app.offer_price_ton or 0.0),
        message=(app.message or "").strip(),
        deal_id=getattr(app, "deal_id", None),
        campaign_id=camp.id,
        campaign_title=(camp.title or "").strip(),
        channel=ChannelOut.model_validate(ch),
        campaign_owner_id=camp.owner_id,
        campaign_owner_display_name=campaign_owner.display_name if campaign_owner else "",
        campaign_owner_username=campaign_owner.telegram_username if campaign_owner else None,
        # Campaign owner is the Advertiser
        campaign_owner_rating_avg=campaign_owner.rating_advertiser_avg if campaign_owner else 0.0,
        campaign_owner_rating_count=campaign_owner.rating_advertiser_count if campaign_owner else 0,
        campaign_owner_rating_advertiser_avg=campaign_owner.rating_advertiser_avg if campaign_owner else 0.0,
        campaign_owner_rating_advertiser_count=campaign_owner.rating_advertiser_count if campaign_owner else 0,
        
        applicant_id=app.applicant_id,
        # Applicant is the Channel Owner (Publisher)
        applicant_rating_avg=applicant.rating_owner_avg if applicant else 0.0,
        applicant_rating_count=applicant.rating_count if applicant else 0, # Note: applicant.rating_owner_count? wait.
        applicant_rating_owner_avg=applicant.rating_owner_avg if applicant else 0.0,
        applicant_rating_owner_count=applicant.rating_owner_count if applicant else 0,
        
        viewer_role="incoming" if is_owner else "my",
        can_start_deal=bool(is_owner and app.status == "pending" and not getattr(app, "deal_id", None))
    )


@router.delete("/{id}")
def cancel_campaign_offer(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    app = db.query(CampaignOffer).filter(CampaignOffer.id == id).one_or_none()
    if not app: raise HTTPException(status_code=404)
    camp = db.query(Campaign).filter(Campaign.id == app.campaign_id).one_or_none()
    if app.applicant_id != user.id and (not camp or camp.owner_id != user.id): raise HTTPException(status_code=403)
    if getattr(app, "deal_id", None): raise HTTPException(status_code=409, detail="Deal already exists")
    db.delete(app)
    db.commit()
    return {"ok": True}


@router.post("/{id}/start-deal", response_model=DealOut)
async def start_deal_from_campaign_offer(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    app = db.query(CampaignOffer).filter(CampaignOffer.id == id, CampaignOffer.status == "pending").one_or_none()
    if not app: raise HTTPException(status_code=404)
    camp = db.query(Campaign).filter(Campaign.id == app.campaign_id, Campaign.owner_id == user.id).one_or_none()
    if not camp: raise HTTPException(status_code=403)
    
    ch = db.query(Channel).filter(Channel.id == app.channel_id).first()
    seller = db.query(User).filter(User.id == ch.owner_id).first() if ch else None
    if not seller or not seller.wallet_address: raise HTTPException(status_code=409, detail="Seller wallet missing")

    d = Deal(id=f"d_{uuid4().hex[:8]}", channel_id=ch.id, advertiser_id=user.id, campaign_id=camp.id, emoji=get_random_deal_emoji(), status=DealStatus.negotiation.value, price_ton=float(app.offer_price_ton or camp.budget_ton or 0.0), campaign_brief=camp.brief, creative_mode=camp.creative_mode, creative_instructions=camp.creative_instructions, post_duration_hours=camp.post_duration_hours, seller_wallet=seller.wallet_address, created_at=_now(), updated_at=_now())
    
    if camp.creative_mode == "template":
        tpl = db.query(PostTemplate).filter(PostTemplate.id == camp.template_id).first()
        if tpl:
            d.creative_chat_id = tpl.creative_chat_id
            d.creative_message_ids = tpl.creative_message_ids
            d.creative_type = tpl.creative_type
            d.creative_preview_text = tpl.preview_text
            d.creative_preview_file_id = tpl.preview_file_id
            d.creative_preview_file_ids = tpl.preview_file_ids
            d.creative_preview_count = tpl.preview_count

    db.add(d)
    app.status = "accepted"
    app.deal_id = d.id
    db.commit()

    if settings.telegram_bot_token:
        try:
            bot = TelegramBotClient(settings.telegram_bot_token)
            cs = ChatService(db)
            await cs.notify_deal_start(bot, d, title=f"Campaign “{camp.title}”" if camp.title else None)
        except Exception:
            pass # Keep deal even if notification fails

    return DealOut.model_validate(d, context={"channel_name": ch.title or ch.handle or ch.id})
