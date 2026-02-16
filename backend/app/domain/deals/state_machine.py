"""
Deals State Machine.
Defines the finite state machine and transition logic for advertising deals.
Handles validation of status changes and side effects during transitions.
"""
from __future__ import annotations

"""
State machine (decision layer).

ARCHITECTURE RULES:
1) Deal state is controlled ONLY here.
2) Escrow is side-effect-only (infrastructure), NOT a decision maker.
3) TON logic is accessed via an adapter (EscrowService).

IMPORTANT:
- Keep this minimal. No extra flows or statuses beyond what the API already exposes.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from app.db.models.deal import DealStatus


@dataclass(frozen=True)
class EscrowResult:
    success: bool
    tx_hash: str | None = None
    error: str | None = None
    details: dict[str, Any] | None = None


@runtime_checkable
class EscrowProtocol(Protocol):
    def create_escrow(self, deal: dict) -> dict: ...
    async def check_balance(self, address: str) -> float: ...
    async def release(self, escrow_wallet_id: str, to_address: str, amount_ton: float) -> EscrowResult: ...
    async def refund(self, escrow_wallet_id: str, to_address: str) -> EscrowResult: ...

# Constants
BALANCE_TOLERANCE_TON = 0.001  # Small tolerance (epsilon) for rounding/fees


class TransitionConflict(Exception):
    """Raised when a transition is not allowed for current status/role."""


@dataclass(frozen=True)
class TransitionResult:
    deal: dict
    escrow: EscrowResult | None = None


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _expected_amount_ton(deal: dict) -> float:
    # Deal price is stored in TON in `price_ton`
    # Use expected_amount_ton if set, otherwise fallback to price_ton
    val = deal.get("expected_amount_ton") or deal.get("price_ton") or 0
    try:
        return float(val)
    except Exception:
        return 0.0


def _is_allowed_transition(from_status: str, to_status: str) -> bool:
    allowed = {
        # Existing project flow:
        # negotiation -> pending_payment -> creative_draft -> creative_review -> approved -> posted -> released
        (DealStatus.negotiation.value, DealStatus.pending_payment.value),  # accept
        (DealStatus.pending_payment.value, DealStatus.creative_draft.value),  # confirm_payment (real) 
        (DealStatus.approved.value, DealStatus.scheduling.value),  # request slot
        (DealStatus.scheduled.value, DealStatus.posted.value),  # publish scheduled post
        (DealStatus.posted.value, DealStatus.released.value),  # release (funds release after publication)
        (DealStatus.creative_draft.value, DealStatus.creative_review.value),  # creative received via bot
        (DealStatus.creative_review.value, DealStatus.approved.value),  # approve (owner)
        (DealStatus.creative_review.value, DealStatus.creative_draft.value),  # reject (owner)
        (DealStatus.approved.value, DealStatus.scheduling.value),  # request slot
        (DealStatus.approved.value, DealStatus.scheduling.value),  # request slot
        (DealStatus.scheduling.value, DealStatus.scheduled.value),  # approve slot
        (DealStatus.scheduling.value, DealStatus.awaiting_confirmation.value), # approve slot -> awaiting (new flow)
        (DealStatus.scheduled.value, DealStatus.awaiting_confirmation.value), # legacy/re-check
        (DealStatus.awaiting_confirmation.value, DealStatus.scheduled.value), # confirm_deal

        (DealStatus.negotiation.value, DealStatus.cancelled.value),  # cancel/decline
        (DealStatus.pending_payment.value, DealStatus.cancelled.value),  # cancel
        (DealStatus.pending_payment.value, DealStatus.creative_review.value), # confirm_payment with template
        # Cancel with refund (if funds were held):
        (DealStatus.creative_draft.value, DealStatus.refunded.value),
        (DealStatus.creative_review.value, DealStatus.refunded.value),
        (DealStatus.approved.value, DealStatus.refunded.value),
        (DealStatus.scheduling.value, DealStatus.refunded.value),
        (DealStatus.scheduled.value, DealStatus.refunded.value),
        (DealStatus.awaiting_confirmation.value, DealStatus.refunded.value),
    }
    return (from_status, to_status) in allowed


async def transition(
    *,
    deal: dict,
    action: str,
    actor: str,
    escrow: EscrowProtocol,
    payload: dict | None = None,
) -> TransitionResult:
    """
    Transition a deal. Async version.

    Parameters:
    - deal: mutable dict representing the deal record (mock store)
    - action: "accept" | "pay" | "confirm_payment" | "creative" | "approve" | "request_edits" | "release" | "cancel" | "decline" | "publish" | "request_slot" | "approve_slot"
    - actor: "advertiser" | "channel_owner" | "pr_manager" | "system"
    - escrow: EscrowService (side-effects only)
    - payload: optional data (e.g. creative text)

    Returns TransitionResult with optional escrow side-effect result.
    """

    payload = payload or {}
    status = deal["status"]

    # NOTE: permissions are mocked; this is a *shape* for future real checks.
    if action == "accept":
        if actor not in ("channel_owner", "system") or status != DealStatus.negotiation.value:
            raise TransitionConflict("Cannot accept in current state")
        if not _is_allowed_transition(status, DealStatus.pending_payment.value):
            raise TransitionConflict("Invalid transition")
        deal["status"] = DealStatus.pending_payment.value
        return TransitionResult(deal=deal)

    if action == "decline":
        if actor != "channel_owner" or status != DealStatus.negotiation.value:
            raise TransitionConflict("Cannot decline in current state")
        if not _is_allowed_transition(status, DealStatus.cancelled.value):
            raise TransitionConflict("Invalid transition")
        deal["status"] = DealStatus.cancelled.value
        deal["cancelled_by"] = "channel_owner"
        deal["cancelled_at"] = _now_iso()
        return TransitionResult(deal=deal)

    if action == "cancel":
        # Cancellation logic:
        # - negotiation/pending_payment -> cancelled
        # - any state with funds -> refunded
        if actor not in ("advertiser", "channel_owner", "system"):
            raise TransitionConflict("Only advertiser, owner, or system can cancel")
        
        if status in (DealStatus.negotiation.value, DealStatus.pending_payment.value):
            if not _is_allowed_transition(status, DealStatus.cancelled.value):
                raise TransitionConflict("Invalid transition to cancelled")
            deal["status"] = DealStatus.cancelled.value
            deal["cancelled_by"] = actor
            deal["cancelled_at"] = _now_iso()
            return TransitionResult(deal=deal)
        
        # States with funds (must be refunded)
        fund_states = (
            DealStatus.creative_draft.value,
            DealStatus.creative_review.value,
            DealStatus.approved.value,
            DealStatus.scheduling.value,
            DealStatus.scheduled.value,
            DealStatus.awaiting_confirmation.value,
        )
        if status in fund_states:
            if not _is_allowed_transition(status, DealStatus.refunded.value):
                raise TransitionConflict("Invalid transition to refunded")
            # NOTE: Actual refund (TON transfer) is triggered by the caller,
            # but the SM marks the intent.
            deal["status"] = DealStatus.refunded.value
            deal["cancelled_by"] = actor
            deal["cancelled_at"] = _now_iso()
            # Store the state it was cancelled from for UX/audit.
            deal["cancelled_from_status"] = status
            return TransitionResult(deal=deal)
            
        raise TransitionConflict(f"Cannot cancel in current state: {status}")

    if action == "pay":
        # Real TON escrow flow:
        # - /pay creates escrow wallet address and returns instructions
        # - user manually transfers TON
        # - confirm_payment moves status -> creative_draft
        if actor != "advertiser" or status != DealStatus.pending_payment.value:
            raise TransitionConflict("Cannot pay in current state")

        # Create escrow wallet (offline derivation, mostly sync logic).
        try:
            escrow_info = escrow.create_escrow(deal)
        except Exception as e:  # noqa: BLE001
            return TransitionResult(deal=deal, escrow=EscrowResult(success=False, error=str(e)))

        deal["expected_amount_ton"] = _expected_amount_ton(deal)

        return TransitionResult(deal=deal, escrow=EscrowResult(success=True, details=escrow_info))

    if action == "confirm_payment":
        # Manual confirmation endpoint (idempotent).
        if status == DealStatus.creative_draft.value or status == DealStatus.approved.value or status == DealStatus.released.value:
            return TransitionResult(deal=deal)
        if status != DealStatus.pending_payment.value:
            raise TransitionConflict("Cannot confirm payment in current state")

        address = deal.get("escrow_address")
        if not address:
            raise TransitionConflict("Escrow address not created yet. Call /pay first.")

        # ASYNC CHECK
        bal = await escrow.check_balance(str(address))
        expected = _expected_amount_ton(deal)
        
        # Add a small tolerance (epsilon) for rounding/fees
        if bal >= (expected - BALANCE_TOLERANCE_TON):
            # Check if we already have creative data (e.g. from template)
            has_creative = deal.get("creative_message_ids") and deal.get("creative_type")
            
            if has_creative:
                 if not _is_allowed_transition(status, DealStatus.creative_review.value):
                     raise TransitionConflict("Invalid transition to creative_review")
                 deal["status"] = DealStatus.creative_review.value
                 deal["waiting_for_creative"] = 0
                 # Preserve existing creative fields
            else:
                 if not _is_allowed_transition(status, DealStatus.creative_draft.value):
                     raise TransitionConflict("Invalid transition to creative_draft")
                 deal["status"] = DealStatus.creative_draft.value
                 deal["waiting_for_creative"] = 1
                 deal["creative_chat_id"] = None
                 deal["creative_message_ids"] = None
                 deal["creative_type"] = None

            deal["payment_confirmed_at"] = _now_iso()
            return TransitionResult(deal=deal)
        
        return TransitionResult(deal=deal, escrow=EscrowResult(success=False, error=f"Insufficient balance: {bal} < {expected}"))

    if action == "creative":
        # Bot-first creative: submissions can be from advertiser (default) or channel owner (custom_task).
        # This action is invoked by the Telegram update handler after it stores message references.
        creative_mode = deal.get("creative_mode", "template")
        expected_actor = "channel_owner" if creative_mode == "custom_task" else "advertiser"

        if actor != expected_actor or status != DealStatus.creative_draft.value:
            raise TransitionConflict(f"Cannot submit creative as {actor} in current state (expected {expected_actor})")

        if not deal.get("waiting_for_creative"):
            # idempotent: if we already received a creative, do nothing
            if status == DealStatus.creative_review.value:
                return TransitionResult(deal=deal)
        if not _is_allowed_transition(status, DealStatus.creative_review.value):
            raise TransitionConflict("Invalid transition")

        # Store only Telegram references (no text in DB).
        deal["creative_chat_id"] = payload.get("creative_chat_id", deal.get("creative_chat_id"))
        deal["creative_message_ids"] = payload.get("creative_message_ids", deal.get("creative_message_ids"))
        deal["creative_type"] = payload.get("creative_type", deal.get("creative_type"))
        deal["waiting_for_creative"] = 0
        deal["status"] = DealStatus.creative_review.value
        deal["creative_received_at"] = _now_iso()
        return TransitionResult(deal=deal)

    if action == "approve":
        # Approvals can be from channel owner (template) or advertiser (custom_task).
        creative_mode = deal.get("creative_mode", "template")
        expected_actor = "advertiser" if creative_mode == "custom_task" else "channel_owner"

        if actor != expected_actor or status != DealStatus.creative_review.value:
            raise TransitionConflict(f"Cannot approve as {actor} in current state (expected {expected_actor})")

        if not _is_allowed_transition(status, DealStatus.approved.value):
            raise TransitionConflict("Invalid transition")
        deal["status"] = DealStatus.approved.value
        deal["approved_at"] = _now_iso()
        return TransitionResult(deal=deal)

    if action == "request_edits":
        # Reject flow: requests for a new version from channel owner (template) or advertiser (custom_task).
        # creative_review -> creative_draft + waiting_for_creative=true
        creative_mode = deal.get("creative_mode", "template")
        expected_actor = "advertiser" if creative_mode == "custom_task" else "channel_owner"

        if actor != expected_actor or status != DealStatus.creative_review.value:
            raise TransitionConflict(f"Cannot request edits as {actor} in current state (expected {expected_actor})")

        if not _is_allowed_transition(status, DealStatus.creative_draft.value):
            raise TransitionConflict("Invalid transition")
        deal["status"] = DealStatus.creative_draft.value
        deal["waiting_for_creative"] = 1
        # Clear old references; new creative will overwrite.
        deal["creative_chat_id"] = None
        deal["creative_message_ids"] = None
        deal["creative_type"] = None
        deal["edits_requested_at"] = _now_iso()
        return TransitionResult(deal=deal)

    if action == "publish":
        # Publish post to channel (approved -> posted, no funds release)
        if actor not in ("channel_owner", "system") or status not in (DealStatus.approved.value, DealStatus.scheduled.value):
            raise TransitionConflict("Cannot publish in current state")
        if not _is_allowed_transition(status, DealStatus.posted.value):
            raise TransitionConflict("Invalid transition")
        deal["status"] = DealStatus.posted.value
        # published_at and published_channel_id are set in endpoint after successful publication
        return TransitionResult(deal=deal)

    if action == "request_slot":
        # Advertiser requests a specific publishing slot within channel availability.
        if actor != "advertiser" or status not in (DealStatus.approved.value, DealStatus.scheduling.value):
            raise TransitionConflict("Cannot request slot in current state")
        preferred = (payload.get("preferred_publish_at") or "").strip()
        if not preferred:
            raise TransitionConflict("Missing preferred_publish_at")
        if status == DealStatus.approved.value and not _is_allowed_transition(status, DealStatus.scheduling.value):
            raise TransitionConflict("Invalid transition")
        deal["preferred_publish_at"] = preferred
        deal["status"] = DealStatus.scheduling.value
        return TransitionResult(deal=deal)

    if action == "approve_slot":
        # Channel owner confirms the requested slot; deal becomes scheduled.
        if actor != "channel_owner" or status != DealStatus.scheduling.value:
            raise TransitionConflict("Cannot approve slot in current state")
        if not _is_allowed_transition(status, DealStatus.awaiting_confirmation.value):
            raise TransitionConflict("Invalid transition")
        if not deal.get("preferred_publish_at"):
            raise TransitionConflict("Missing preferred_publish_at")
        deal["scheduled_at"] = deal.get("preferred_publish_at")
        deal["status"] = DealStatus.awaiting_confirmation.value # Scheduled -> Awaiting Confirmation
        return TransitionResult(deal=deal)

    if action == "confirm_deal":
        # Final confirmation by both parties
        if actor not in ("advertiser", "channel_owner") or status != DealStatus.awaiting_confirmation.value:
             raise TransitionConflict("Cannot confirm deal in current state")
        
        if actor == "advertiser":
             deal["deal_confirmed_by_advertiser"] = 1
        elif actor == "channel_owner":
             deal["deal_confirmed_by_channel"] = 1
        
        if deal.get("deal_confirmed_by_advertiser") and deal.get("deal_confirmed_by_channel"):
             deal["status"] = DealStatus.scheduled.value
             deal["deal_confirmed_at"] = _now_iso()
        
        return TransitionResult(deal=deal)

    if action == "release":
        if actor not in ("advertiser", "system") or status != DealStatus.posted.value:
            raise TransitionConflict("Cannot release in current state")
        if not _is_allowed_transition(status, DealStatus.released.value):
            raise TransitionConflict("Invalid transition")
        deal["status"] = DealStatus.released.value
        return TransitionResult(deal=deal)

    raise TransitionConflict("Unknown action")
