"""
Deals Permissions.
Implements granular access control checks for deal-related operations 
based on user roles (Advertiser vs. Channel Owner) and deal states.
"""
from __future__ import annotations

import logging

from app.db.models.deal import Deal, DealStatus
from app.schemas.deal import DealPermissions

logger = logging.getLogger(__name__)

# Constants
CREATIVE_MODE_TEMPLATE = "template"
CREATIVE_MODE_CUSTOM_TASK = "custom_task"

# Cancellable statuses
CANCELLABLE_STATUSES = (
    DealStatus.negotiation.value,
    DealStatus.pending_payment.value,
    DealStatus.creative_draft.value,
    DealStatus.creative_review.value,
    DealStatus.approved.value,
    DealStatus.scheduling.value,
    DealStatus.scheduled.value,
    DealStatus.awaiting_confirmation.value,
)


def _get_creative_submitter(creative_mode: str) -> str:
    """
    Determine who submits creative based on creative_mode.
    
    Returns:
        "advertiser" for template mode, "channel_owner" for custom_task mode
    """
    return "channel_owner" if creative_mode == CREATIVE_MODE_CUSTOM_TASK else "advertiser"


def _get_creative_reviewer(creative_mode: str) -> str:
    """
    Determine who reviews creative based on creative_mode.
    
    Returns:
        "advertiser" for custom_task mode, "channel_owner" for template mode
    """
    return "advertiser" if creative_mode == CREATIVE_MODE_CUSTOM_TASK else "channel_owner"


def compute_deal_permissions(
    *,
    status: str,
    is_advertiser: bool,
    is_channel_owner: bool,
    is_pr_manager: bool,
    negotiation_confirmed_by_advertiser: bool = False,
    negotiation_confirmed_by_channel: bool = False,
    creative_mode: str = CREATIVE_MODE_TEMPLATE,
    negotiation_confirmed_by_me: bool = False,
    negotiation_confirmed_by_other: bool = False,
    deal_confirmed_by_advertiser: bool = False,
    deal_confirmed_by_channel: bool = False,
    post_not_found: bool = False,
    duration_set: bool = False,
    has_reviewed: bool = False,
    payment_made: bool = False,
) -> DealPermissions:
    """
    Mock permissions calculator.

    IMPORTANT:
    - It exists to define response shape (`permissions`) for the frontend.
    """

    can_confirm_terms = (
        status == DealStatus.negotiation.value
        and is_advertiser
        and duration_set
        and not negotiation_confirmed_by_advertiser
    )

    # Confirm deal (both sides)
    can_confirm_deal = (
        status == DealStatus.awaiting_confirmation.value
        and (
            (is_advertiser and not deal_confirmed_by_advertiser)
            or (is_channel_owner and not deal_confirmed_by_channel)
        )
    )
    
    can_accept = (
        status == DealStatus.negotiation.value
        and is_channel_owner
        and negotiation_confirmed_by_advertiser
    )
    
    can_pay = (
        status == DealStatus.pending_payment.value
        and is_advertiser
        and not is_pr_manager
    )
    
    # Bot-first creative flow:
    # - Advertiser (template) or Channel Owner (custom_task) submits creative via Telegram bot
    # - The other side reviews in Mini App
    submitter = _get_creative_submitter(creative_mode)
    can_submit_creative = (
        status == DealStatus.creative_draft.value
        and (
            (submitter == "advertiser" and is_advertiser)
            or (submitter == "channel_owner" and is_channel_owner)
        )
    )
    
    reviewer = _get_creative_reviewer(creative_mode)
    can_approve = (
        status == DealStatus.creative_review.value
        and (
            (reviewer == "advertiser" and is_advertiser)
            or (reviewer == "channel_owner" and is_channel_owner)
        )
    )
    can_request_edits = (
        status == DealStatus.creative_review.value
        and (
            (reviewer == "advertiser" and is_advertiser)
            or (reviewer == "channel_owner" and is_channel_owner)
        )
    )
    
    can_cancel = (
        status in CANCELLABLE_STATUSES
        and (is_advertiser or is_channel_owner)
    )
    
    # Variant A scheduling:
    can_request_slot = (
        status in (DealStatus.approved.value, DealStatus.scheduling.value)
        and is_advertiser
    )
    can_approve_slot = (
        status == DealStatus.scheduling.value
        and is_channel_owner
    )
    
    can_use_template = (
        status == DealStatus.creative_draft.value
        and is_advertiser
        and creative_mode == CREATIVE_MODE_TEMPLATE
    )
    
    # Publish is now handled exclusively by the bot. Manual publication from Mini App is disabled.
    can_publish = False
    
    can_release = (
        status == DealStatus.posted.value
        and is_advertiser
        and post_not_found
    )

    can_review = (
        (
            status in (DealStatus.released.value, DealStatus.refunded.value)
            or (status == DealStatus.cancelled.value and payment_made)
        )
        and (is_advertiser or is_channel_owner)
        and not has_reviewed
    )

    logger.debug(
        f"Computed permissions for status={status}, creative_mode={creative_mode}",
        extra={
            "status": status,
            "creative_mode": creative_mode,
            "is_advertiser": is_advertiser,
            "is_channel_owner": is_channel_owner,
            "permissions": {
                "can_confirm_terms": can_confirm_terms,
                "can_pay": can_pay,
                "can_submit_creative": can_submit_creative,
                "can_approve": can_approve,
                "can_cancel": can_cancel,
            },
        },
    )

    return DealPermissions(
        can_accept=can_accept,
        can_confirm_deal=can_confirm_deal,
        can_confirm_terms=can_confirm_terms,
        can_pay=can_pay,
        can_submit_creative=can_submit_creative,
        can_approve=can_approve,
        can_approve_creative=can_approve,
        can_request_edits=can_request_edits,
        can_cancel=can_cancel,
        can_request_slot=can_request_slot,
        can_approve_slot=can_approve_slot,
        can_use_template=can_use_template,
        can_publish=can_publish,
        can_release=can_release,
        can_review=can_review,
        negotiation_confirmed_by_me=False,
        negotiation_confirmed_by_other=False,
    )
