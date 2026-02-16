"""
Campaign management router.
Public campaign feed, campaign creation by advertiser,
channel application to join a campaign.
"""
from __future__ import annotations
from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db
from app.db.models.campaign import Campaign, CampaignStatus
from app.db.models.campaign_offer import CampaignOffer
from app.db.models.channel import Channel
from app.db.models.user import User
from app.schemas.campaign import CampaignCreateIn, CampaignOut
from app.schemas.campaign_offer import CampaignApplyIn, CampaignOfferOut

router = APIRouter()

def _now() -> datetime: return datetime.utcnow()


@router.get("", response_model=list[CampaignOut])
def list_campaigns(db: Session = Depends(get_db)):
    """Public feed: only open campaigns."""
    campaigns = db.query(Campaign).filter(Campaign.status == CampaignStatus.open).order_by(Campaign.created_at.desc()).all()
    owner_ids = list({c.owner_id for c in campaigns})
    users = {u.id: u for u in db.query(User).filter(User.id.in_(owner_ids)).all()} if owner_ids else {}
    result = []
    for c in campaigns:
        out = CampaignOut.model_validate(c)
        owner = users.get(c.owner_id)
        if owner:
            out.owner_rating_avg = owner.rating_advertiser_avg
            out.owner_rating_count = owner.rating_advertiser_count
        result.append(out)
    return result


@router.get("/my", response_model=list[CampaignOut])
def list_my_campaigns(user=CurrentUser, db: Session = Depends(get_db)):
    """User's own campaigns with owner rating populated."""
    campaigns = db.query(Campaign).filter(Campaign.owner_id == user.id).order_by(Campaign.created_at.desc()).all()
    result = []
    for c in campaigns:
        out = CampaignOut.model_validate(c)
        # In this context, owner is the current user
        out.owner_rating_avg = user.rating_advertiser_avg
        out.owner_rating_count = user.rating_advertiser_count
        result.append(out)
    return result


@router.post("", response_model=CampaignOut)
def create_campaign(payload: CampaignCreateIn, user=CurrentUser, db: Session = Depends(get_db)):
    c = Campaign(id=f"c_{uuid4().hex[:10]}", owner_id=user.id, title=payload.title.strip(), brief=payload.brief.strip(), category=(payload.category or "").strip(), language=(payload.language or "").strip(), budget_ton=float(payload.budget_ton or 0.0), desired_views_24h=payload.desired_views_24h, template_id=payload.template_id if payload.creative_mode == "template" else "", creative_mode=payload.creative_mode or "template", creative_instructions=payload.creative_instructions, post_duration_hours=payload.post_duration_hours, status=CampaignStatus.open, created_at=_now(), updated_at=_now())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.get("/{id}", response_model=CampaignOut)
def get_campaign(id: str, db: Session = Depends(get_db)):
    c = db.query(Campaign).filter(Campaign.id == id).one_or_none()
    if not c: raise HTTPException(status_code=404)
    out = CampaignOut.model_validate(c)
    owner = db.query(User).filter(User.id == c.owner_id).one_or_none()
    if owner:
        out.owner_rating_avg = owner.rating_advertiser_avg
        out.owner_rating_count = owner.rating_advertiser_count
    return out


@router.delete("/{id}", response_model=CampaignOut)
def delete_campaign(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    c = db.query(Campaign).filter(Campaign.id == id).one_or_none()
    if not c or c.owner_id != user.id: raise HTTPException(status_code=403)
    out = c
    db.query(CampaignOffer).filter(CampaignOffer.campaign_id == id).delete()
    db.delete(c)
    db.commit()
    return out


@router.post("/{id}/apply", response_model=CampaignOfferOut)
def apply_to_campaign(id: str, payload: CampaignApplyIn, user=CurrentUser, db: Session = Depends(get_db)):
    camp = db.query(Campaign).filter(Campaign.id == id, Campaign.status == CampaignStatus.open).one_or_none()
    if not camp: raise HTTPException(status_code=404)
    ch = db.query(Channel).filter(Channel.id == payload.channel_id, Channel.owner_id == user.id).one_or_none()
    if not ch or not ch.is_verified: raise HTTPException(status_code=403)

    app = CampaignOffer(id=f"ca_{uuid4().hex[:10]}", campaign_id=id, channel_id=payload.channel_id, applicant_id=user.id, offer_price_ton=float(payload.offer_price_ton or 0.0), message=(payload.message or "").strip(), status="pending", created_at=_now())
    db.add(app)
    db.commit()
    db.refresh(app)
    return app
