"""
User reviews and ratings router.
Review creation after deal completion, fetching reviews
per user, average rating calculation.
"""
from __future__ import annotations
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db
from app.db.models.channel import Channel
from app.db.models.deal import Deal, DealStatus
from app.db.models.campaign import Campaign
from app.db.models.review import Review
from app.db.models.user import User
from app.schemas.review import ReviewCreateIn, ReviewOut
from uuid import uuid4

router = APIRouter()
logger = logging.getLogger(__name__)

REVIEWABLE_STATUSES = (DealStatus.released.value, DealStatus.refunded.value)


def _get_reviewer_anonymized_name(db: Session, review: Review) -> str:
    deal = db.query(Deal).filter(Deal.id == review.deal_id).one_or_none()
    if not deal:
        reviewer = db.query(User).filter(User.id == review.reviewer_id).one_or_none()
        return reviewer.display_name if reviewer else "User"

    if review.reviewer_id == deal.advertiser_id:
        return "Advertiser"

    channel = db.query(Channel).filter(Channel.id == deal.channel_id).one_or_none()
    if channel:
        return "Channel author"

    reviewer = db.query(User).filter(User.id == review.reviewer_id).one_or_none()
    return reviewer.display_name if reviewer else "User"


def _recalc_user_rating(db: Session, user_id: str) -> None:
    # 1. Calculate Advertiser rating (where target_channel_id IS NULL)
    adv_res = db.query(
        func.avg(Review.rating),
        func.count(Review.id),
    ).filter(
        Review.target_user_id == user_id,
        Review.target_channel_id.is_(None)
    ).first()
    
    # 2. Calculate Owner rating (where target_channel_id IS NOT NULL)
    own_res = db.query(
        func.avg(Review.rating),
        func.count(Review.id),
    ).filter(
        Review.target_user_id == user_id,
        Review.target_channel_id.is_not(None)
    ).first()

    adv_avg = float(adv_res[0] or 0)
    adv_count = int(adv_res[1] or 0)
    
    own_avg = float(own_res[0] or 0)
    own_count = int(own_res[1] or 0)

    # General rating (for backward compatibility if needed)
    all_res = db.query(
        func.avg(Review.rating),
        func.count(Review.id),
    ).filter(Review.target_user_id == user_id).first()
    all_avg = float(all_res[0] or 0)
    all_count = int(all_res[1] or 0)

    db.query(User).filter(User.id == user_id).update({
        User.rating_advertiser_avg: round(adv_avg, 2),
        User.rating_advertiser_count: adv_count,
        User.rating_owner_avg: round(own_avg, 2),
        User.rating_owner_count: own_count,
        # Legacy
        User.rating_avg: round(all_avg, 2),
        User.rating_count: all_count,
    })


def _recalc_channel_rating(db: Session, channel_id: str) -> None:
    result = db.query(
        func.avg(Review.rating),
        func.count(Review.id),
    ).filter(Review.target_channel_id == channel_id).first()
    avg_val = float(result[0] or 0)
    count_val = int(result[1] or 0)
    db.query(Channel).filter(Channel.id == channel_id).update({
        Channel.rating_avg: round(avg_val, 2),
        Channel.rating_count: count_val,
    })


def _recalc_campaign_rating(db: Session, campaign_id: str) -> None:
    result = db.query(
        func.avg(Review.rating),
        func.count(Review.id),
    ).filter(Review.target_campaign_id == campaign_id).first()
    avg_val = float(result[0] or 0)
    count_val = int(result[1] or 0)
    db.query(Campaign).filter(Campaign.id == campaign_id).update({
        Campaign.rating_avg: round(avg_val, 2),
        Campaign.rating_count: count_val,
    })


@router.post("/deals/{deal_id}/review", response_model=ReviewOut)
def create_review(
    deal_id: str,
    payload: ReviewCreateIn,
    user=CurrentUser,
    db: Session = Depends(get_db),
):
    deal = db.query(Deal).filter(Deal.id == deal_id).one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    is_cancelled_after_payment = (
        deal.status == DealStatus.cancelled.value and bool(deal.payment_confirmed_at)
    )
    if deal.status not in REVIEWABLE_STATUSES and not is_cancelled_after_payment:
        raise HTTPException(status_code=409, detail="Deal is not in a reviewable state")

    is_advertiser = deal.advertiser_id.strip() == user.id.strip()
    channel = db.query(Channel).filter(Channel.id == deal.channel_id).one_or_none()
    is_channel_owner = bool(channel and channel.owner_id.strip() == user.id.strip())

    if not is_advertiser and not is_channel_owner:
        raise HTTPException(status_code=403, detail="Access denied")

    if is_advertiser and (not channel or channel.owner_id is None):
        raise HTTPException(status_code=400, detail="Channel owner not found, cannot submit review")

    existing = db.query(Review).filter(
        Review.deal_id == deal_id,
        Review.reviewer_id == user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="You have already reviewed this deal")
    if is_advertiser:
        target_user_id = channel.owner_id if channel else deal.channel.owner_id
        target_channel_id = deal.channel_id
        target_campaign_id = None
    else:
        target_user_id = deal.advertiser_id
        target_channel_id = None
        target_campaign_id = deal.campaign_id

    review = Review(
        id=f"rev_{uuid4().hex[:8]}",
        deal_id=deal_id,
        reviewer_id=user.id,
        target_user_id=target_user_id,
        target_channel_id=target_channel_id,
        target_campaign_id=target_campaign_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    # Both targets set simultaneously is invalid; both absent is OK for deals without a campaign
    if review.target_channel_id and review.target_campaign_id:
        raise HTTPException(status_code=500, detail="Internal error: invalid review target")
    db.add(review)
    db.flush()

    _recalc_user_rating(db, target_user_id)
    if target_channel_id:
        _recalc_channel_rating(db, target_channel_id)
    if target_campaign_id:
        _recalc_campaign_rating(db, target_campaign_id)

    db.commit()
    db.refresh(review)

    out = ReviewOut.model_validate(review)
    out.reviewer_name = _get_reviewer_anonymized_name(db, review)
    return out


@router.get("/deals/{deal_id}/reviews", response_model=list[ReviewOut])
def get_deal_reviews(
    deal_id: str,
    user=CurrentUser,
    db: Session = Depends(get_db),
):
    deal = db.query(Deal).filter(Deal.id == deal_id).one_or_none()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    reviews = db.query(Review).filter(Review.deal_id == deal_id).all()
    result = []
    for r in reviews:
        out = ReviewOut.model_validate(r)
        out.reviewer_name = _get_reviewer_anonymized_name(db, r)
        result.append(out)
    return result


@router.get("/deals/{deal_id}/my-review", response_model=ReviewOut | None)
def get_my_review(
    deal_id: str,
    user=CurrentUser,
    db: Session = Depends(get_db),
):
    review = db.query(Review).filter(
        Review.deal_id == deal_id,
        Review.reviewer_id == user.id,
    ).first()
    if not review:
        return None
    out = ReviewOut.model_validate(review)
    out.reviewer_name = _get_reviewer_anonymized_name(db, review)
    return out


@router.get("/users/{user_id}/reviews", response_model=list[ReviewOut])
def get_user_reviews(
    user_id: str,
    role: str | None = None, # 'advertiser' or 'owner'
    db: Session = Depends(get_db),
):
    query = db.query(Review).filter(Review.target_user_id == user_id)
    
    if role == 'advertiser':
        # Roles were: target_channel_id IS NULL for advertiser
        query = query.filter(Review.target_channel_id.is_(None))
    elif role == 'owner':
        # target_channel_id IS NOT NULL for channel owner
        query = query.filter(Review.target_channel_id.is_not(None))

    reviews = query.order_by(Review.created_at.desc()).limit(50).all()
    result = []
    for r in reviews:
        out = ReviewOut.model_validate(r)
        out.reviewer_name = _get_reviewer_anonymized_name(db, r)
        result.append(out)
    return result


@router.get("/channels/{channel_id}/reviews", response_model=list[ReviewOut])
def get_channel_reviews(
    channel_id: str,
    db: Session = Depends(get_db),
):
    reviews = db.query(Review).filter(Review.target_channel_id == channel_id).order_by(Review.created_at.desc()).limit(50).all()
    result = []
    for r in reviews:
        out = ReviewOut.model_validate(r)
        out.reviewer_name = _get_reviewer_anonymized_name(db, r)
        result.append(out)
    return result


@router.get("/campaigns/{campaign_id}/reviews", response_model=list[ReviewOut])
def get_campaign_reviews(
    campaign_id: str,
    db: Session = Depends(get_db),
):
    reviews = db.query(Review).filter(Review.target_campaign_id == campaign_id).order_by(Review.created_at.desc()).limit(50).all()
    result = []
    for r in reviews:
        out = ReviewOut.model_validate(r)
        out.reviewer_name = _get_reviewer_anonymized_name(db, r)
        result.append(out)
    return result
