from __future__ import annotations

import logging
import json
import math
from datetime import datetime, timezone
from uuid import uuid4
from typing import Final

from sqlalchemy.orm import Session

from app.domain.exceptions import (
    NotFoundError, ForbiddenError, ConflictError, ValidationError, InfrastructureError,
)

from app.core.config import settings
from app.infra.events import bus as signals
from app.db.models.channel import Channel
from app.db.models.deal import Deal, DealStatus, get_random_deal_emoji
from app.db.models.user import User
from app.infra.telegram.bot_client import TelegramBotClient, TelegramApiError
from app.domain.deals.state_machine import TransitionConflict, transition, TransitionResult
from app.infra.ton.escrow import TonEscrowService
from app.infra.ton.webhook_manager import ton_webhook_manager
from app.infra.queue.rq import get_queue, get_scheduler
from app.domain.chat.service import ChatService
from app.domain.deals.mappers import (
    deal_to_dict as _deal_to_dict,
    apply_deal_dict as _apply_deal_dict,
    ALLOWED_UPDATE_FIELDS,
)
from app.domain.scheduling.slots import (
    parse_hhmm as _parse_hhmm,
    parse_local_datetime as _parse_local_yyyy_mm_dd_thhmm,
    iso_z as _iso_z,
    slot_round_key as _slot_round_key,
    tzinfo_or_utc as _tzinfo_or_utc,
)

logger = logging.getLogger(__name__)

# --- Constants: Events ---
EVENT_CREATED: Final[str] = "created"
EVENT_TERMS_CONFIRMED: Final[str] = "terms_confirmed"
EVENT_DEAL_CONFIRMED: Final[str] = "deal_confirmed"
EVENT_PENDING_PAYMENT: Final[str] = "pending_payment"
EVENT_PAYMENT_INITIATED: Final[str] = "payment_initiated"
EVENT_SLOT_REQUESTED: Final[str] = "slot_requested"
EVENT_SLOT_APPROVED: Final[str] = "slot_approved"
EVENT_CREATIVE_SUBMITTED: Final[str] = "creative_submitted"
EVENT_CREATIVE_APPROVED: Final[str] = "creative_approved"
EVENT_EDITS_REQUESTED: Final[str] = "edits_requested"
EVENT_ACCEPTED: Final[str] = "accepted"
EVENT_PUBLISHED: Final[str] = "published"
EVENT_RELEASED: Final[str] = "released"
EVENT_CANCELLED: Final[str] = "cancelled"
EVENT_REFUNDED: Final[str] = "refunded"

# --- Constants: Actors ---
ACTOR_ADVERTISER: Final[str] = "advertiser"
ACTOR_OWNER: Final[str] = "channel_owner"
ACTOR_SYSTEM: Final[str] = "system"

# --- Helpers: Time & Scheduling ---

def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

def _calculate_deal_price(channel: Channel, post_duration_hours: int, top_duration_hours: int) -> float:
    """
    Calculates deal price based on flexible pricing formula with progressive top:
    Price = (Base Price * ceil(Duration / 24)) + Σ(n=1 to N) [TopPrice * (1 + (n-1) * StepPct/100)]
    Which simplifies to: TotalTop = P * (N + (N * (N - 1) / 2) * (R / 100))
    """
    base_price = channel.price_per_post_ton or 0.0
    top_price_hour = getattr(channel, "price_top_hour_ton", 0.0) or 0.0
    step_pct = getattr(channel, "top_price_step_pct", 0.0) or 0.0
    
    multiplier = math.ceil(post_duration_hours / 24) if post_duration_hours > 0 else 1
    total_base = base_price * multiplier
    
    # Progressive top calculation
    # Sum = N*P + P*(R/100) * (0 + 1 + ... + N-1)
    # Sum = N*P + P*(R/100) * (N*(N-1)/2)
    n = top_duration_hours
    if n > 0:
        total_top = n * top_price_hour + top_price_hour * (step_pct / 100.0) * (n * (n - 1) / 2.0)
    else:
        total_top = 0.0
    
    return round(total_base + total_top, 4)

# --- Helpers: Access Control & Validation ---

def _get_deal_or_404(db: Session, deal_id: str) -> Deal:
    deal = db.query(Deal).filter(Deal.id == deal_id).one_or_none()
    if not deal:
        raise NotFoundError("Deal")
    return deal

def _check_access(db: Session, deal: Deal, user_id: str, required_role: str | None = None) -> str:
    """
    Checks if user is part of the deal. Returns the role.
    FIX: Handles lazy loading of channel safely.
    """
    is_advertiser = deal.advertiser_id == user_id
    
    # Safely determine channel owner
    channel_owner_id = None
    if deal.channel:
        channel_owner_id = deal.channel.owner_id
    elif deal.channel_id:
        # Fallback if relationship not loaded
        channel_owner_id = db.query(Channel.owner_id).filter(Channel.id == deal.channel_id).scalar()

    is_owner = channel_owner_id == user_id

    if not is_advertiser and not is_owner:
        raise ForbiddenError()

    role = ACTOR_ADVERTISER if is_advertiser else ACTOR_OWNER
    
    if required_role and role != required_role:
        raise ForbiddenError(f"Forbidden: User is not {required_role}")
        
    return role

async def _verify_bot_admin(channel: Channel) -> None:
    """Verifies that the bot is an administrator in the Telegram channel."""
    if not settings.telegram_bot_token or not settings.telegram_bot_id:
        raise InfrastructureError("Telegram bot is not configured")
    
    if not channel.telegram_channel_id:
        raise ConflictError("Channel is not verified yet")

    tg = TelegramBotClient(settings.telegram_bot_token)
    try:
        bot_member = await tg.get_chat_member(channel.telegram_channel_id, int(settings.telegram_bot_id))
    except TelegramApiError as e:
        logger.error(f"Telegram getChatMember failed: {e.message}")
        raise InfrastructureError(f"Telegram check failed: {e.message}")

    if bot_member.get("status") != "administrator":
        raise ConflictError("Bot was not added as admin")

# --- Helpers: Background Jobs ---

def _schedule_publication_job(deal: Deal) -> None:
    """Schedules the RQ job for deal publication."""
    try:
        from app.tasks.publish_deal_post import publish_deal_post
        raw = str(deal.scheduled_at or "").strip()
        if raw.endswith("Z"): raw = raw.replace("Z", "+00:00")
        
        run_at = datetime.fromisoformat(raw)
        if run_at.tzinfo is None: run_at = run_at.replace(tzinfo=timezone.utc)
        run_at = run_at.astimezone(timezone.utc)
        job_id = f"publish_deal_{deal.id}_{int(run_at.timestamp())}"
        
        get_scheduler().enqueue_at(run_at, publish_deal_post, deal.id, job_id=job_id)
        logger.info(f"Scheduled publication job {job_id} for deal {deal.id} at {run_at}")
    except Exception as e:
        logger.error(f"Failed to schedule publication for {deal.id}: {e}", exc_info=True)

def _cancel_publication_job(deal: Deal) -> None:
    """Cancels the RQ job if it exists."""
    if not deal.scheduled_at: return
    try:
        raw = str(deal.scheduled_at).strip()
        if raw.endswith("Z"): raw = raw.replace("Z", "+00:00")
        run_at = datetime.fromisoformat(raw)
        if run_at.tzinfo is None: run_at = run_at.replace(tzinfo=timezone.utc)
        
        job_id = f"publish_deal_{deal.id}_{int(run_at.timestamp())}"
        get_scheduler().cancel(job_id)
        logger.info(f"Cancelled publication job {job_id} for deal {deal.id}")
    except Exception as e:
        logger.warning(f"Failed to cancel RQ job for {deal.id}: {e}")

# --- Helper: Transition Application ---

async def _apply_transition(
    db: Session, 
    deal: Deal, 
    action: str, 
    actor: str, 
    user_id: str, 
    payload: dict | None = None,
    ton_service: TonEscrowService | None = None
) -> TransitionResult:
    """
    Executes a state validation and applies the transition.
    Handles caching, commits, and signal emission.
    """
    service = ton_service or TonEscrowService()
    
    try:
        # AWAIT HERE
        res = await transition(
            deal=_deal_to_dict(deal), 
            action=action, 
            actor=actor, 
            escrow=service, 
            payload=payload
        )
    except TransitionConflict as e:
        raise ConflictError(str(e))

    # Apply changes
    _apply_deal_dict(deal, res.deal)
    deal.updated_at = datetime.utcnow()
    
    # Commit
    db.commit()
    db.refresh(deal)
    
    # Emit signal (event type inferred unless passed explicitly, but usually inferred from status or action)
    # We map action/status to Event Type for signals
    event_type = _infer_event_type(action, deal.status)
    if event_type:
        await signals.deal_updated.emit(signals.DealEvent(deal_id=deal.id, actor_id=user_id, event_type=event_type))
        
    return res

def _infer_event_type(action: str, status: str) -> str | None:
    # Map actions to events logic
    if action == "request_slot": return EVENT_SLOT_REQUESTED
    if action == "approve_slot": return EVENT_SLOT_APPROVED
    if action == "accept": return EVENT_ACCEPTED
    if action == "approve": return EVENT_CREATIVE_APPROVED
    if action == "request_edits": return EVENT_EDITS_REQUESTED
    if action == "creative": return EVENT_CREATIVE_SUBMITTED
    if action == "cancel": return EVENT_CANCELLED # or refunded, handled by logic
    if action == "decline": return EVENT_CANCELLED
    if action == "confirm_deal": return EVENT_DEAL_CONFIRMED
    # For others like 'pay' or 'confirm_payment', handled specifically in callers
    return None

# --- Action Handlers ---

async def create_deal_action(
    db: Session, 
    user_id: str, 
    channel_id: str, 
    creative_instructions: str = "",
    preferred_publish_at: str | None = None,
    post_duration_hours: int | None = None,
    top_duration_hours: int = 0,
    campaign_id: str | None = None,
    campaign_brief: str = "",
    creative_mode: str = "template",
) -> Deal:
    channel = db.query(Channel).filter(Channel.id == channel_id).one_or_none()
    if not channel:
        raise NotFoundError("Channel")

    if not channel.is_verified:
        raise ConflictError("Channel not verified (bot admin check failed previously)")

    # Verify bot rights again to keep data clean
    await _verify_bot_admin(channel)

    # Get seller wallet
    owner = db.query(User).filter(User.id == channel.owner_id).one_or_none() if channel.owner_id else None
    seller_wallet = owner.wallet_address if owner else None

    # Create Deal
    deal_id = f"d_{uuid4().hex[:8]}"
    d = Deal(
        id=deal_id,
        channel_id=channel_id,
        advertiser_id=user_id,
        campaign_id=campaign_id,
        emoji=get_random_deal_emoji(),
        status=DealStatus.negotiation.value,
        ad_format="post",
        price_ton=_calculate_deal_price(channel, post_duration_hours or 24, top_duration_hours),
        campaign_brief=campaign_brief,
        creative_mode=creative_mode,
        creative_instructions=creative_instructions,
        preferred_publish_at=preferred_publish_at,
        post_duration_hours=post_duration_hours or 24,
        top_duration_hours=top_duration_hours,
        creative_text="",
        seller_wallet=seller_wallet,
        created_at=datetime.utcnow(),
    )
    db.add(d)
    db.commit()
    db.refresh(d)

    logger.info(f"Deal created: {d.id} by {user_id}")

    await signals.deal_updated.emit(signals.DealEvent(
        deal_id=d.id, 
        actor_id=user_id, 
        event_type=EVENT_CREATED,
        metadata={"channel_title": channel.title or channel.handle or ""}
    ))
    return d

async def request_slot_action(db: Session, deal_id: str, user_id: str, local_datetime: str) -> Deal:
    deal = _get_deal_or_404(db, deal_id)
    _check_access(db, deal, user_id, required_role=ACTOR_ADVERTISER)
    
    if deal.status not in (DealStatus.approved.value, DealStatus.scheduling.value):
        raise ConflictError("Invalid status for slot request")

    # Time slot validation
    channel = deal.channel
    tzinfo, _ = _tzinfo_or_utc(channel.posting_timezone)
    slot_minutes = int(channel.posting_slot_minutes or 30)

    try:
        y, mo, d, hh, mm = _parse_local_yyyy_mm_dd_thhmm(local_datetime)
        local_dt = datetime(y, mo, d, hh, mm, tzinfo=tzinfo)
    except Exception: 
        raise ValidationError("Invalid datetime format")

    if local_dt < datetime.now(tz=tzinfo):
        raise ValidationError("Cannot request a slot in the past")

    # Collision Check
    key = _slot_round_key(local_dt, slot_minutes)
    other_deals = db.query(Deal).filter(
        Deal.channel_id == channel.id, 
        Deal.id != deal_id,
        Deal.status.in_([DealStatus.scheduling.value, DealStatus.scheduled.value, DealStatus.posted.value, DealStatus.released.value])
    ).all()
    
    for od in other_deals:
        raw = (od.scheduled_at or od.preferred_publish_at or "").strip()
        if not raw: continue
        try:
            if raw.endswith("Z"): raw = raw.replace("Z", "+00:00")
            dt_loc = datetime.fromisoformat(raw).astimezone(tzinfo)
            if _slot_round_key(dt_loc, slot_minutes) == key:
                raise ConflictError("Slot already taken")
        except ConflictError:
            raise
        except Exception: 
             continue

    preferred_utc = _iso_z(local_dt)
    
    await _apply_transition(db, deal, "request_slot", ACTOR_ADVERTISER, user_id, {"preferred_publish_at": preferred_utc})
    return deal

async def approve_slot_action(db: Session, deal_id: str, user_id: str) -> Deal:
    deal = _get_deal_or_404(db, deal_id)
    _check_access(db, deal, user_id, required_role=ACTOR_OWNER)

    await _apply_transition(db, deal, "approve_slot", ACTOR_OWNER, user_id)
    
    # NOTE: We do NOT schedule publication here anymore. 
    # Status is now awaiting_confirmation. Scheduling happens after confirm_deal.
    return deal

async def confirm_deal_action(db: Session, deal_id: str, user_id: str, payload: dict) -> Deal:
    deal = _get_deal_or_404(db, deal_id)
    role = _check_access(db, deal, user_id) # advertiser or channel_owner

    # Transition
    await _apply_transition(db, deal, "confirm_deal", role, user_id, payload)
    
    # If became scheduled (both confirmed), schedule the job
    if deal.status == DealStatus.scheduled.value:
         _schedule_publication_job(deal)
         
    return deal

async def accept_deal_action(db: Session, deal_id: str, user_id: str) -> Deal:
    deal = _get_deal_or_404(db, deal_id)
    _check_access(db, deal, user_id, required_role=ACTOR_OWNER)

    await _apply_transition(db, deal, "accept", ACTOR_OWNER, user_id)
    return deal

async def _execute_cancellation(db: Session, deal: Deal, actor: str, actor_id: str) -> Deal:
    """Shared cancellation logic for both user and system-triggered cancellation."""
    old_status = deal.status

    ton_service = TonEscrowService()
    try:
        res = await transition(deal=_deal_to_dict(deal), action="cancel", actor=actor, escrow=ton_service)
    except TransitionConflict as e:
        raise ConflictError(str(e))

    if old_status == DealStatus.scheduled.value:
        _cancel_publication_job(deal)

    if res.deal["status"] == DealStatus.refunded.value:
        await _process_automatic_refund(db, deal, res, ton_service)

    _apply_deal_dict(deal, res.deal)
    deal.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(deal)

    try:
        ChatService(db).clear_deal_context(deal.id)
    except Exception:
        pass

    event_type = EVENT_CANCELLED if res.deal["status"] == "cancelled" else EVENT_REFUNDED
    await signals.deal_updated.emit(signals.DealEvent(deal_id=deal.id, actor_id=actor_id, event_type=event_type))

    return deal

async def cancel_deal_action(db: Session, deal_id: str, user_id: str) -> Deal:
    deal = _get_deal_or_404(db, deal_id)
    role = _check_access(db, deal, user_id)
    return await _execute_cancellation(db, deal, role, user_id)

async def _process_automatic_refund(db: Session, deal: Deal, res: TransitionResult, ton_service: TonEscrowService):
    advertiser = db.query(User).get(deal.advertiser_id)
    if not advertiser or not advertiser.wallet_address:
         # Log warning but don't fail, manual intervention might be needed
        logger.warning(f"Skipping refund for {deal.id}: Invalid advertiser wallet")
        return

    amount = float(deal.expected_amount_ton or deal.price_ton or 0)
    if amount <= 0 or not deal.escrow_wallet_id:
        logger.warning(f"Skipping refund for {deal.id}: Amount {amount} or no escrow")
        return

    logger.info(f"Initiating refund for {deal.id}: {amount} TON -> {advertiser.wallet_address}")
    
    escrow_res = await ton_service.refund(
        escrow_wallet_id=deal.escrow_wallet_id,
        to_address=advertiser.wallet_address,
    )
    
    if escrow_res.success:
        res.deal["refund_tx_hash"] = escrow_res.tx_hash
        res.deal["refunded_at"] = _now_iso()
        logger.info(f"Refund successful for {deal.id}, tx: {escrow_res.tx_hash}")
    else:
        logger.error(f"Refund failed for {deal.id}: {escrow_res.error}")

async def cancel_deal_by_system(db: Session, deal_id: str) -> Deal:
    deal = _get_deal_or_404(db, deal_id)
    return await _execute_cancellation(db, deal, ACTOR_SYSTEM, ACTOR_SYSTEM)

async def confirm_terms_action(db: Session, deal_id: str, user_id: str, payload: dict | None = None) -> Deal:
    deal = _get_deal_or_404(db, deal_id)
    role = _check_access(db, deal, user_id)
    payload = payload or {}

    # Save post_duration_hours/top_duration_hours if advertiser provides it
    if role == ACTOR_ADVERTISER:
        if "post_duration_hours" in payload:
            deal.post_duration_hours = int(payload["post_duration_hours"])
        if "top_duration_hours" in payload:
            deal.top_duration_hours = int(payload["top_duration_hours"])
        
        # Recalculate price
        deal.price_ton = _calculate_deal_price(deal.channel, deal.post_duration_hours or 24, deal.top_duration_hours)

    # Clean logic for flag updates
    changed = False
    adv_confirmed = bool(deal.negotiation_confirmed_by_advertiser)
    ch_confirmed = bool(deal.negotiation_confirmed_by_channel)

    if role == ACTOR_ADVERTISER and not adv_confirmed:
        deal.negotiation_confirmed_by_advertiser = True
        changed = True
        adv_confirmed = True
    elif role == ACTOR_OWNER and not ch_confirmed:
        deal.negotiation_confirmed_by_channel = True
        changed = True
        ch_confirmed = True

    if changed:
        deal.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(deal)
        await signals.deal_updated.emit(signals.DealEvent(deal_id=deal.id, actor_id=user_id, event_type=EVENT_TERMS_CONFIRMED))

    # Trigger system transition if both agreed
    if adv_confirmed and ch_confirmed and deal.status == DealStatus.negotiation.value:
         await _apply_transition(db, deal, "accept", ACTOR_SYSTEM, ACTOR_SYSTEM) # System accepts

    return deal

async def pay_deal_action(db: Session, deal_id: str, user_id: str) -> dict:
    deal = _get_deal_or_404(db, deal_id)
    _check_access(db, deal, user_id, required_role=ACTOR_ADVERTISER)

    # Use explicit transition call because we need specific error handling for escrow formation
    ton_service = TonEscrowService()
    try:
        # AWAIT HERE
        res = await transition(deal=_deal_to_dict(deal), action="pay", actor=ACTOR_ADVERTISER, escrow=ton_service)
    except TransitionConflict as e:
        raise ConflictError(str(e))
        
    if res.escrow and not res.escrow.success:
        raise ConflictError(res.escrow.error or "TON escrow error")

    _apply_deal_dict(deal, res.deal)
    db.commit()
    await signals.deal_updated.emit(signals.DealEvent(deal_id=deal.id, actor_id=user_id, event_type=EVENT_PAYMENT_INITIATED))

    if deal.escrow_address and ton_webhook_manager._webhook_id is not None:
        try:
            await ton_webhook_manager.subscribe_account(str(deal.escrow_address))
        except Exception:
            logger.warning("Failed to subscribe escrow address to webhook", exc_info=True)

    return {
        "escrow_address": deal.escrow_address or "mock",
        "amount_ton": float(deal.expected_amount_ton or deal.price_ton or 0),
        "network": deal.escrow_network or "mock",
        "instruction": f"Send exactly {deal.expected_amount_ton or deal.price_ton} TON to this address",
    }

async def approve_creative_action(db: Session, deal_id: str, user_id: str) -> Deal:
    deal = _get_deal_or_404(db, deal_id)
    
    # Logic depends on creative mode
    creative_mode = deal.creative_mode or "template"
    required_role = ACTOR_ADVERTISER if creative_mode == "custom_task" else ACTOR_OWNER
    _check_access(db, deal, user_id, required_role=required_role)
    actor = required_role # Same as role

    await _apply_transition(db, deal, "approve", actor, user_id)
    return deal

async def request_edits_action(db: Session, deal_id: str, user_id: str) -> Deal:
    deal = _get_deal_or_404(db, deal_id)
    
    creative_mode = deal.creative_mode or "template"
    required_role = ACTOR_ADVERTISER if creative_mode == "custom_task" else ACTOR_OWNER
    _check_access(db, deal, user_id, required_role=required_role)
    actor = required_role

    await _apply_transition(db, deal, "request_edits", actor, user_id)
    return deal

async def _execute_publication(
    db: Session,
    deal: Deal,
    actor: str,
    actor_id: str,
) -> Deal:
    """Shared publication logic for both user and system-triggered publication."""
    channel = deal.channel
    if not channel:
        channel = db.query(Channel).filter(Channel.id == deal.channel_id).one_or_none()
    if not channel or not channel.telegram_channel_id:
        raise ConflictError("Channel Telegram ID missing")
    if not deal.creative_chat_id or not deal.creative_message_ids:
        raise ConflictError("Creative not submitted")

    ton_service = TonEscrowService()
    try:
        res = await transition(deal=_deal_to_dict(deal), action="publish", actor=actor, escrow=ton_service)
    except TransitionConflict as e:
        raise ConflictError(str(e))

    message_ids = json.loads(deal.creative_message_ids or "[]")
    tg = TelegramBotClient(settings.telegram_bot_token)
    try:
        published_ids = await tg.copy_messages(
            chat_id=int(channel.telegram_channel_id),
            from_chat_id=int(deal.creative_chat_id),
            message_ids=[int(x) for x in message_ids],
        )
    except TelegramApiError as e:
        logger.error(f"Publication failed for {deal.id}: {e.message}")
        raise InfrastructureError(f"Failed to publish to Telegram: {e.message}")
    if not published_ids:
        raise InfrastructureError("Telegram copyMessages returned no IDs")

    res.deal["published_at"] = _now_iso()
    res.deal["published_channel_id"] = str(channel.telegram_channel_id)
    res.deal["published_message_ids"] = json.dumps(published_ids)
    res.deal["post_not_found"] = False

    _apply_deal_dict(deal, res.deal)
    deal.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(deal)

    await signals.deal_updated.emit(signals.DealEvent(deal_id=deal.id, actor_id=actor_id, event_type=EVENT_PUBLISHED))

    if deal.post_duration_hours and deal.post_duration_hours > 0:
        _schedule_auto_release_job(deal)

    if deal.top_duration_hours and deal.top_duration_hours > 0:
        _schedule_top_check_job(deal)

    return deal

async def publish_deal_action(db: Session, deal_id: str, user_id: str) -> Deal:
    deal = _get_deal_or_404(db, deal_id)
    _check_access(db, deal, user_id, required_role=ACTOR_OWNER)
    return await _execute_publication(db, deal, ACTOR_OWNER, user_id)

def _schedule_top_check_job(deal: Deal) -> None:
    """Schedules a check that the post is still last in the channel after top_duration_hours."""
    try:
        from app.tasks.check_top import check_top_task
        from datetime import timedelta

        hours = int(deal.top_duration_hours or 0)
        if hours <= 0:
            return

        run_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        job_id = f"check_top_{deal.id}_{int(run_at.timestamp())}"

        get_scheduler().enqueue_at(run_at, check_top_task, deal.id, job_id=job_id)
        logger.info(f"Scheduled top-check job {job_id} for deal {deal.id} at {run_at}")
    except Exception as e:
        logger.error(f"Failed to schedule top-check for {deal.id}: {e}", exc_info=True)

def _schedule_auto_release_job(deal: Deal) -> None:
    """Schedules the auto-release task."""
    try:
        from app.tasks.auto_release import auto_release_task
        from datetime import timedelta
        
        hours = int(deal.post_duration_hours or 0)
        if hours <= 0: return

        run_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        job_id = f"auto_release_{deal.id}_{int(run_at.timestamp())}"
        
        get_scheduler().enqueue_at(run_at, auto_release_task, deal.id, job_id=job_id)
        logger.info(f"Scheduled auto-release job {job_id} for deal {deal.id} at {run_at}")
    except Exception as e:
        logger.error(f"Failed to schedule auto-release for {deal.id}: {e}", exc_info=True)

async def release_funds_action(db: Session, deal_id: str, user_id: str) -> Deal:
    deal = _get_deal_or_404(db, deal_id)
    
    if deal.status == DealStatus.released.value:
        return deal
    
    if user_id != ACTOR_SYSTEM:
        _check_access(db, deal, user_id, required_role=ACTOR_ADVERTISER)

    channel = deal.channel
    if not channel:
        channel = db.query(Channel).filter(Channel.id == deal.channel_id).one_or_none()
    owner = db.query(User).filter(User.id == channel.owner_id).one_or_none() if channel and channel.owner_id else None
    seller_wallet = owner.wallet_address if owner else None
    if not seller_wallet: 
        raise ConflictError("Seller wallet not set")

    if not deal.seller_wallet or deal.seller_wallet != seller_wallet:
        deal.seller_wallet = seller_wallet
        db.commit()

    actor = ACTOR_SYSTEM if user_id == ACTOR_SYSTEM else ACTOR_ADVERTISER
    ton_service = TonEscrowService()
    try:
        res = await transition(deal=_deal_to_dict(deal), action="release", actor=actor, escrow=ton_service)
    except TransitionConflict as e:
        raise ConflictError(str(e))
    
    escrow_wallet_id = str(deal.escrow_wallet_id or "")
    if not escrow_wallet_id: 
        raise ConflictError("No escrow wallet")

    amount = float(deal.expected_amount_ton or deal.price_ton or 0)
    escrow_res = await ton_service.release(escrow_wallet_id=escrow_wallet_id, to_address=seller_wallet, amount_ton=amount)
    
    if not escrow_res.success: 
        raise InfrastructureError(escrow_res.error or "Blockchain release failed")

    res.deal["release_tx_hash"] = escrow_res.tx_hash
    res.deal["released_at"] = _now_iso()
    
    _apply_deal_dict(deal, res.deal)
    db.commit()
    db.refresh(deal)

    try: ChatService(db).clear_deal_context(deal.id)
    except Exception: pass

    await signals.deal_updated.emit(signals.DealEvent(deal_id=deal.id, actor_id=user_id, event_type=EVENT_RELEASED))
    return deal

async def submit_creative_action(db: Session, deal_id: str, user_id: str) -> Deal:
    deal = _get_deal_or_404(db, deal_id)
    if deal.status != DealStatus.creative_draft.value:
         # Strict check before heavy lifting
        raise ConflictError("Deal state changed or not found")
        
    role = _check_access(db, deal, user_id)
    
    payload = {
        "creative_chat_id": deal.creative_chat_id,
        "creative_message_ids": json.loads(deal.creative_message_ids or "[]"),
        "creative_type": deal.creative_type,
    }
    
    await _apply_transition(db, deal, "creative", role, user_id, payload)
    return deal

async def update_deal_action(
    db: Session,
    deal_id: str,
    user_id: str,
    post_duration_hours: int | None = None,
    top_duration_hours: int | None = None,
) -> Deal:
    deal = _get_deal_or_404(db, deal_id)
    _check_access(db, deal, user_id, required_role=ACTOR_ADVERTISER)

    if deal.status != DealStatus.negotiation.value:
        raise ConflictError("Cannot update deal after negotiation")

    changed = False
    if post_duration_hours is not None:
        deal.post_duration_hours = post_duration_hours
        changed = True
    if top_duration_hours is not None:
        deal.top_duration_hours = top_duration_hours
        changed = True

    if changed:
        deal.price_ton = _calculate_deal_price(deal.channel, deal.post_duration_hours or 24, deal.top_duration_hours or 0)
        deal.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(deal)

        await signals.deal_updated.emit(signals.DealEvent(deal_id=deal.id, actor_id=user_id, event_type=EVENT_TERMS_CONFIRMED))

    return deal

async def use_template_action(db: Session, deal_id: str, user_id: str, template_id: str) -> Deal:
    from app.db.models.post_template import PostTemplate

    deal = _get_deal_or_404(db, deal_id)
    _check_access(db, deal, user_id, required_role=ACTOR_ADVERTISER)

    if deal.status != DealStatus.creative_draft.value:
        raise ConflictError("Deal is not in creative_draft state")

    tpl = db.query(PostTemplate).filter(PostTemplate.id == template_id, PostTemplate.owner_id == user_id).one_or_none()
    if not tpl or not tpl.creative_message_ids:
        raise NotFoundError("Template")

    message_ids = json.loads(tpl.creative_message_ids or "[]")
    deal.creative_chat_id = str(tpl.creative_chat_id)
    deal.creative_message_ids = json.dumps(message_ids)
    deal.creative_type = tpl.creative_type or "template"
    deal.creative_preview_text = tpl.preview_text or ""
    deal.creative_preview_file_id = tpl.preview_file_id or ""
    deal.creative_preview_file_ids = getattr(tpl, "preview_file_ids", "") or ""
    deal.creative_preview_count = int(tpl.preview_count or len(message_ids) or 0)
    deal.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(deal)

    await signals.deal_updated.emit(signals.DealEvent(deal_id=deal.id, actor_id=user_id, event_type=EVENT_CREATIVE_SUBMITTED))

    return deal

async def preview_template_action(db: Session, deal_id: str, user_id: str) -> Deal:
    deal = _get_deal_or_404(db, deal_id)
    _check_access(db, deal, user_id, required_role=ACTOR_ADVERTISER)

    if not deal.creative_chat_id or not deal.creative_message_ids:
        raise ConflictError("No template selected yet")

    message_ids = json.loads(deal.creative_message_ids or "[]")
    if settings.telegram_bot_token and user_id.startswith("tg_"):
        tg = TelegramBotClient(settings.telegram_bot_token)
        from_chat_id = str(deal.creative_chat_id)
        target_tg_id = int(user_id.replace("tg_", ""))
        try:
            try:
                await tg.copy_messages(chat_id=str(target_tg_id), from_chat_id=from_chat_id, message_ids=[int(x) for x in message_ids])
            except Exception:
                for mid in message_ids:
                    await tg.copy_message(chat_id=str(target_tg_id), from_chat_id=from_chat_id, message_id=int(mid))
            await tg.send_message(str(target_tg_id), f"Preview of creative for deal #{deal.id} (not submitted yet).")
        except Exception:
            pass

    return deal

async def submit_template_action(db: Session, deal_id: str, user_id: str) -> Deal:
    deal = _get_deal_or_404(db, deal_id)
    _check_access(db, deal, user_id, required_role=ACTOR_ADVERTISER)

    if deal.status != DealStatus.creative_draft.value:
        raise ConflictError(f"Deal is not in creative_draft (current: {deal.status})")
    if not deal.creative_chat_id or not deal.creative_message_ids:
        raise ConflictError("No template selected yet")

    message_ids = json.loads(deal.creative_message_ids or "[]")
    if not isinstance(message_ids, list) or not message_ids:
        raise ConflictError("Template content is corrupted")
    message_ids = [int(x) for x in message_ids]

    payload = {
        "creative_chat_id": str(deal.creative_chat_id),
        "creative_message_ids": message_ids,
        "creative_type": deal.creative_type or "template",
    }

    await _apply_transition(db, deal, "creative", ACTOR_ADVERTISER, user_id, payload)

    channel = deal.channel
    if not channel:
        channel = db.query(Channel).filter(Channel.id == deal.channel_id).one_or_none()
    if channel and channel.owner_id and settings.telegram_bot_token:
        owner_id = channel.owner_id
        if owner_id.startswith("tg_"):
            try:
                tg = TelegramBotClient(settings.telegram_bot_token)
                owner_tg_id = int(owner_id.replace("tg_", ""))
                from_chat_id = str(deal.creative_chat_id)
                try:
                    await tg.copy_messages(chat_id=str(owner_tg_id), from_chat_id=from_chat_id, message_ids=message_ids)
                except Exception:
                    for mid in message_ids:
                        await tg.copy_message(chat_id=str(owner_tg_id), from_chat_id=from_chat_id, message_id=int(mid))
                await tg.send_message(str(owner_tg_id), f"New creative received for deal #{deal.id}. Open the Mini App to approve/reject.")
            except Exception:
                pass

    return deal

async def publish_deal_by_system(db: Session, deal_id: str) -> Deal:
    """System-triggered publication"""
    deal = _get_deal_or_404(db, deal_id)
    return await _execute_publication(db, deal, ACTOR_SYSTEM, ACTOR_SYSTEM)
