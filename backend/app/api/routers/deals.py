"""
Deal lifecycle router.
Creation, payment, confirmation, publishing, release/refund,
WebSocket notifications, creative preview.
"""
from __future__ import annotations
import json
import logging
import httpx
from datetime import datetime
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db
from app.core.config import settings
from app.db.models.channel import Channel
from app.db.models.deal import Deal
from app.db.models.review import Review
from app.db.models.user import User

from app.schemas.deal import (
    DealAcceptOut,
    DealActionOut,
    DealCreateIn,
    DealDetailOut,
    DealOut,
    DealPayInstructionsOut,
    DealRequestSlotIn,
    DealSlotsOut,
    DealConfirmIn,
)
from app.infra.websocket.manager import manager as ws_manager
from app.infra.telegram.bot_client import TelegramBotClient
from app.infra.telegram.webapp_auth import validate_init_data
from app.domain.deals.service import (
    create_deal_action,
    cancel_deal_action,
    request_slot_action,
    approve_slot_action,
    accept_deal_action,
    confirm_terms_action,
    pay_deal_action,
    approve_creative_action,
    request_edits_action,
    publish_deal_action,
    release_funds_action,
    confirm_deal_action,
    update_deal_action,
    use_template_action,
    submit_template_action,
    preview_template_action,
)
from app.domain.deals.permissions import compute_deal_permissions
from app.schemas.post_template import UseTemplateIn
from app.domain.scheduling.slots import tzinfo_or_utc, parse_hhmm, slot_round_key, iso_z
from pydantic import BaseModel, Field


class ConfirmTermsIn(BaseModel):
    post_duration_hours: int | None = Field(default=None, ge=1)
    top_duration_hours: int | None = Field(default=None, ge=0)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("", response_model=DealOut)
async def create_deal(payload: DealCreateIn, user=CurrentUser, db: Session = Depends(get_db)):
    """Create a deal request."""
    d = await create_deal_action(
        db=db,
        user_id=user.id,
        channel_id=payload.channel_id,
        campaign_brief=payload.campaign_brief,
        creative_mode=payload.creative_mode or "template",
        creative_instructions=payload.creative_instructions,
        post_duration_hours=payload.post_duration_hours,
        top_duration_hours=payload.top_duration_hours,
        campaign_id=payload.campaign_id,
    )
    return DealOut.model_validate(d, context={"channel_name": (d.channel.title or d.channel.handle or "").strip() or d.channel_id})

class DealUpdateIn(BaseModel):
    post_duration_hours: int | None = Field(default=None, ge=1)
    top_duration_hours: int | None = Field(default=None, ge=0)

@router.patch("/{id}", response_model=DealOut)
async def update_deal(id: str, payload: DealUpdateIn, user=CurrentUser, db: Session = Depends(get_db)):
    d = await update_deal_action(
        db, id, user.id,
        post_duration_hours=payload.post_duration_hours,
        top_duration_hours=payload.top_duration_hours,
    )
    return DealOut.model_validate(d, context={"channel_name": (d.channel.title or d.channel.handle or "").strip() or d.id})

@router.get("", response_model=list[DealOut])
def list_deals(user=CurrentUser, db: Session = Depends(get_db)):
    """List deals where user is either advertiser or channel owner."""
    deals = (
        db.query(
            Deal,
            Channel.title,
            Channel.handle,
            Channel.subscribers_count,
            Channel.avg_views_24h,
            Channel.category,
            Channel.language,
        )
        .join(Channel, Channel.id == Deal.channel_id)
        .filter((Deal.advertiser_id == user.id) | (Channel.owner_id == user.id))
        .all()
    )
    res = []
    for d, title, handle, subs, views_24h, cat, lang in deals:
        out = DealOut.model_validate(d)
        out.channel_name = (title or handle or "").strip() or d.channel_id
        out.channel_handle = handle or ""
        out.channel_subscribers = subs or 0
        out.channel_avg_views_24h = views_24h or 0
        out.channel_category = cat or ""
        out.channel_language = lang or ""
        res.append(out)
    return res

@router.get("/{id}", response_model=DealDetailOut)
def get_deal(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    deal_obj = (
        db.query(
            Deal,
            Channel.title,
            Channel.handle,
            Channel.subscribers_count,
            Channel.avg_views_24h,
            Channel.category,
            Channel.language,
            Channel.price_per_post_ton,
            Channel.price_top_hour_ton,
            Channel.top_price_step_pct,
        )
        .join(Channel, Channel.id == Deal.channel_id)
        .filter(Deal.id == id)
        .first()
    )
    if not deal_obj:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    d, title, handle, subs, views_24h, cat, lang, price_per_post, price_top, price_step = deal_obj
    deal = DealOut.model_validate(d)
    deal.channel_name = (title or handle or "").strip() or d.channel_id
    deal.channel_handle = handle or ""
    deal.channel_subscribers = subs or 0
    deal.channel_avg_views_24h = views_24h or 0
    deal.channel_category = cat or ""
    deal.channel_language = lang or ""

    is_advertiser = d.advertiser_id == user.id
    is_channel_owner = bool(db.query(Channel).filter(Channel.id == d.channel_id, Channel.owner_id == user.id).first())
    is_pr_manager = False # Role system to be implemented

    confirmed_by_me = (
        (is_advertiser and deal.negotiation_confirmed_by_advertiser)
        or (is_channel_owner and deal.negotiation_confirmed_by_channel)
    )
    confirmed_by_other = (
        (is_advertiser and deal.negotiation_confirmed_by_channel)
        or (is_channel_owner and deal.negotiation_confirmed_by_advertiser)
    )

    has_reviewed = bool(db.query(Review.id).filter(Review.deal_id == id, Review.reviewer_id == user.id).first())

    permissions = compute_deal_permissions(
        status=deal.status,
        is_advertiser=is_advertiser,
        is_channel_owner=is_channel_owner,
        is_pr_manager=is_pr_manager,
        negotiation_confirmed_by_advertiser=deal.negotiation_confirmed_by_advertiser,
        negotiation_confirmed_by_channel=deal.negotiation_confirmed_by_channel,
        creative_mode=deal.creative_mode,
        negotiation_confirmed_by_me=confirmed_by_me,
        negotiation_confirmed_by_other=confirmed_by_other,
        deal_confirmed_by_advertiser=deal.deal_confirmed_by_advertiser,
        deal_confirmed_by_channel=deal.deal_confirmed_by_channel,
        post_not_found=bool(deal.post_not_found),
        duration_set=d.post_duration_hours is not None,
        has_reviewed=has_reviewed,
        payment_made=bool(d.payment_confirmed_at),
    )

    channel_obj = db.query(Channel).filter(Channel.id == d.channel_id).one_or_none()
    advertiser_obj = db.query(User).filter(User.id == d.advertiser_id).one_or_none()

    return DealDetailOut(
        **deal.model_dump(),
        permissions=permissions,
        channel_rating_avg=channel_obj.rating_avg if channel_obj else 0.0,
        channel_rating_count=channel_obj.rating_count if channel_obj else 0,
        advertiser_rating_avg=advertiser_obj.rating_avg if advertiser_obj else 0.0,
        advertiser_rating_count=advertiser_obj.rating_count if advertiser_obj else 0,
        channel_price_per_post_ton=float(price_per_post or 0.0),
        channel_price_top_hour_ton=float(price_top or 0.0),
        channel_top_price_step_pct=float(price_step or 0.0),
    )

@router.websocket("/{id}/ws")
async def deal_websocket(
    websocket: WebSocket,
    id: str,
    initData: str = Query(default=""),
    db: Session = Depends(get_db)
):
    await websocket.accept()
    try:
        tg_user = validate_init_data(initData, settings.telegram_bot_token)
    except Exception:
        await websocket.close(code=4003)
        return

    uid = f"tg_{tg_user.id}"
    d = db.query(Deal).filter(Deal.id == id).one_or_none()
    if not d:
        await websocket.close(code=4004)
        return

    is_advertiser = d.advertiser_id == uid
    is_owner = bool(d.channel and d.channel.owner_id == uid)

    if not (is_advertiser or is_owner):
        await websocket.close(code=4003)
        return

    await ws_manager.connect(websocket, id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, id)

@router.get("/{id}/posting-slots", response_model=DealSlotsOut)
def get_deal_posting_slots(
    id: str,
    day: str = Query(default="", description="Date in channel timezone: YYYY-MM-DD"),
    user=CurrentUser,
    db: Session = Depends(get_db),
):
    deal_obj = db.query(Deal).filter(Deal.id == id).one_or_none()
    if not deal_obj:
        raise HTTPException(status_code=404, detail="Deal not found")

    channel = db.query(Channel).filter(Channel.id == deal_obj.channel_id).one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    is_advertiser = deal_obj.advertiser_id == user.id
    is_owner = bool(channel.owner_id == user.id)
    if not (is_advertiser or is_owner):
        raise HTTPException(status_code=403, detail="Access denied")

    # Timezone and slots logic moved to domain/scheduling/slots.py or kept here if simple
    from datetime import datetime, time, timedelta, timezone
    tzinfo, tz = tzinfo_or_utc((getattr(channel, "posting_timezone", None) or "UTC").strip() or "UTC")

    window_start = getattr(channel, "posting_window_start", None) or "10:00"
    window_end = getattr(channel, "posting_window_end", None) or "20:00"
    slot_minutes = int(getattr(channel, "posting_slot_minutes", 30) or 30)
    
    try:
        sh, sm = parse_hhmm(window_start)
        eh, em = parse_hhmm(window_end)
    except Exception:
        sh, sm, eh, em = 10, 0, 20, 0
        window_start, window_end = "10:00", "20:00"

    from datetime import date
    if day.strip():
        try:
            target_day = date.fromisoformat(day)
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid day")
    else:
        target_day = datetime.now(tz=tzinfo).date()

    start_local = datetime.combine(target_day, time(sh, sm), tzinfo=tzinfo)
    end_local = datetime.combine(target_day, time(eh, em), tzinfo=tzinfo)
    if end_local <= start_local: end_local += timedelta(days=1)

    busy: set[str] = set()
    other_deals = db.query(Deal).filter(Deal.channel_id == channel.id, Deal.id != deal_obj.id).all()
    for od in other_deals:
        raw = (od.scheduled_at or od.preferred_publish_at or "").strip()
        if not raw: continue
        try:
            if raw.endswith("Z"): raw = raw.replace("Z", "+00:00")
            dt_loc = datetime.fromisoformat(raw).astimezone(tzinfo)
            if dt_loc.date() == target_day: busy.add(slot_round_key(dt_loc, slot_minutes))
        except Exception: continue

    slots: list[dict] = []
    cur = start_local
    while cur < end_local:
        key = slot_round_key(cur, slot_minutes)
        slots.append({
            "key": key,
            "local": key,
            "utc": iso_z(cur),
            "busy": (key in busy or cur < datetime.now(tz=tzinfo)),
            "requested": key == (slot_round_key(datetime.fromisoformat(deal_obj.preferred_publish_at.replace("Z","+00:00")).astimezone(tzinfo), slot_minutes) if deal_obj.preferred_publish_at else None),
            "scheduled": key == (slot_round_key(datetime.fromisoformat(deal_obj.scheduled_at.replace("Z","+00:00")).astimezone(tzinfo), slot_minutes) if deal_obj.scheduled_at else None),
        })
        cur += timedelta(minutes=slot_minutes)

    return {
        "timezone": tz,
        "window_start": window_start,
        "window_end": window_end,
        "slot_minutes": slot_minutes,
        "date": target_day.isoformat(),
        "slots": slots,
    }

@router.post("/{id}/request-slot", response_model=DealActionOut)
async def request_deal_slot(id: str, payload: DealRequestSlotIn, user=CurrentUser, db: Session = Depends(get_db)):
    d = await request_slot_action(db, id, user.id, payload.local_datetime)
    return {"deal": DealOut.model_validate(d)}

@router.post("/{id}/approve-slot", response_model=DealActionOut)
async def approve_deal_slot(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    d = await approve_slot_action(db, id, user.id)
    return {"deal": DealOut.model_validate(d)}

@router.post("/{id}/cancel", response_model=DealActionOut)
async def cancel_deal(id: str, db: Session = Depends(get_db), user=CurrentUser):
    d = await cancel_deal_action(db, id, user.id)
    return {"deal": DealOut.model_validate(d)}

@router.get("/{id}/preview-media")
async def get_deal_preview_media(
    id: str,
    initData: str = Query(default=""),
    i: int = Query(default=0, ge=0, le=10),
    db: Session = Depends(get_db),
):
    deal_obj = db.query(Deal).filter(Deal.id == id).one_or_none()
    if not deal_obj: raise HTTPException(status_code=404, detail="Deal not found")
    
    try:
        tg_user = validate_init_data(initData, settings.telegram_bot_token)
    except Exception: raise HTTPException(status_code=401)
    
    # Simple access check
    if deal_obj.advertiser_id != f"tg_{tg_user.id}" and (not deal_obj.channel or deal_obj.channel.owner_id != f"tg_{tg_user.id}"):
        raise HTTPException(status_code=403)

    # File ID extraction
    file_id = ""
    try:
        arr = json.loads(deal_obj.creative_preview_file_ids or "[]")
        if 0 <= i < len(arr): file_id = arr[i]
    except Exception: pass
    if not file_id and i == 0: file_id = deal_obj.creative_preview_file_id
    
    if not file_id: raise HTTPException(status_code=404)
    
    bot = TelegramBotClient(settings.telegram_bot_token)
    file_info = await bot.get_file(file_id)
    file_path = file_info.get("file_path")
    if not file_path: raise HTTPException(status_code=404)

    url = f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{file_path}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        return Response(content=r.content, media_type=r.headers.get("content-type"))

@router.post("/{id}/accept", response_model=DealAcceptOut)
async def accept_deal_endpoint(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    d = await accept_deal_action(db, id, user.id)
    return {"deal": DealOut.model_validate(d)}

@router.post("/{id}/confirm-terms", response_model=DealAcceptOut)
async def confirm_terms_endpoint(id: str, payload: ConfirmTermsIn = Body(default=ConfirmTermsIn()), user=CurrentUser, db: Session = Depends(get_db)):
    d = await confirm_terms_action(db, id, user.id, payload.model_dump(exclude_none=True))
    return {"deal": DealOut.model_validate(d)}

@router.post("/{id}/pay", response_model=DealPayInstructionsOut)
async def pay_deal_endpoint(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    return await pay_deal_action(db, id, user.id)

@router.post("/{id}/approve", response_model=DealActionOut)
async def approve_creative_endpoint(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    d = await approve_creative_action(db, id, user.id)
    return {"deal": DealOut.model_validate(d)}

@router.post("/{id}/request-edits", response_model=DealActionOut)
async def request_edits_endpoint(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    d = await request_edits_action(db, id, user.id)
    return {"deal": DealOut.model_validate(d)}

@router.post("/{id}/publish", response_model=DealActionOut)
async def publish_endpoint(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    d = await publish_deal_action(db, id, user.id)
    return {"deal": DealOut.model_validate(d)}

@router.post("/{id}/confirm-deal", response_model=DealActionOut)
async def confirm_deal_endpoint(id: str, payload: DealConfirmIn, user=CurrentUser, db: Session = Depends(get_db)):
    d = await confirm_deal_action(db, id, user.id, payload.model_dump())
    return {"deal": DealOut.model_validate(d)}


@router.post("/{id}/release", response_model=DealActionOut)
async def release_endpoint(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    d = await release_funds_action(db, id, user.id)
    return {"deal": DealOut.model_validate(d)}

@router.post("/{id}/use-template")
async def use_template_for_deal(id: str, payload: UseTemplateIn, user=CurrentUser, db: Session = Depends(get_db)):
    await use_template_action(db, id, user.id, payload.template_id)
    return {"ok": True}

@router.post("/{id}/preview-template", response_model=DealActionOut)
async def preview_template(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    d = await preview_template_action(db, id, user.id)
    return {"deal": DealOut.model_validate(d)}

@router.post("/{id}/submit-template", response_model=DealActionOut)
async def submit_template(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    d = await submit_template_action(db, id, user.id)
    return {"deal": DealOut.model_validate(d)}
