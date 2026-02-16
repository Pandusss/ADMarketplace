"""
Post template management router.
Template CRUD, linking a template to a deal,
submitting a creative from a template.
"""
from __future__ import annotations
import json
import httpx
from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db
from app.core.config import settings
from app.db.models.campaign import Campaign, CampaignStatus
from app.db.models.deal import Deal, DealStatus
from app.db.models.post_template import PostTemplate
from app.db.models.channel import Channel
from app.schemas.deal import DealActionOut
from app.schemas.post_template import PostTemplateCreateIn, PostTemplateOut, UseTemplateIn
from app.infra.ton.escrow import TonEscrowService
from app.infra.telegram.bot_client import TelegramBotClient
from app.infra.telegram.webapp_auth import validate_init_data, TelegramWebAppAuthError
from app.infra.websocket.manager import manager as ws_manager
from app.domain.deals.service import transition
from app.domain.deals.mappers import deal_to_dict

router = APIRouter()

def _tpl_to_out(t: PostTemplate) -> PostTemplateOut:
    return PostTemplateOut.model_validate(t)

def _is_template_public_for_user(template_id: str, user_id: str, db: Session) -> bool:
    tpl = db.query(PostTemplate).filter(PostTemplate.id == template_id).one_or_none()
    if not tpl: return False
    if tpl.owner_id == user_id: return True
    return db.query(Campaign).filter(Campaign.template_id == template_id, Campaign.status == CampaignStatus.open).first() is not None

@router.get("", response_model=list[PostTemplateOut])
def list_templates(user=CurrentUser, db: Session = Depends(get_db)):
    items = db.query(PostTemplate).filter(PostTemplate.owner_id == user.id).order_by(PostTemplate.created_at.desc()).all()
    return [_tpl_to_out(x) for x in items]

@router.post("", response_model=PostTemplateOut)
def create_template(payload: PostTemplateCreateIn, user=CurrentUser, db: Session = Depends(get_db)):
    tpl = PostTemplate(id=f"tpl_{uuid4().hex[:10]}", owner_id=user.id, title=payload.title.strip(), waiting_for_content=True, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return _tpl_to_out(tpl)

@router.get("/{id}", response_model=PostTemplateOut)
def get_template(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    tpl = db.query(PostTemplate).filter(PostTemplate.id == id).one_or_none()
    if not tpl or not _is_template_public_for_user(id, user.id, db): raise HTTPException(status_code=404)
    return _tpl_to_out(tpl)

@router.delete("/{id}")
def delete_template(id: str, user=CurrentUser, db: Session = Depends(get_db)):
    tpl = db.query(PostTemplate).filter(PostTemplate.id == id).one_or_none()
    if not tpl or tpl.owner_id != user.id: raise HTTPException(status_code=404)
    db.delete(tpl)
    db.commit()
    return {"ok": True}

@router.get("/{id}/preview-media")
async def get_template_preview_media(id: str, initData: str = Query(default=""), i: int = Query(default=0, ge=0, le=10), db: Session = Depends(get_db)):
    try: tg_user = validate_init_data(initData, settings.telegram_bot_token)
    except: raise HTTPException(status_code=401)
    
    tpl = db.query(PostTemplate).filter(PostTemplate.id == id).one_or_none()
    if not tpl or not _is_template_public_for_user(id, f"tg_{tg_user.id}", db): raise HTTPException(status_code=404)
    
    file_id = ""
    try:
        arr = json.loads(tpl.preview_file_ids or "[]")
        if 0 <= i < len(arr): file_id = arr[i]
    except: pass
    if not file_id and i == 0: file_id = tpl.preview_file_id
    if not file_id: raise HTTPException(status_code=404)

    bot = TelegramBotClient(settings.telegram_bot_token)
    file_info = await bot.get_file(file_id)
    file_path = file_info.get("file_path")
    if not file_path: raise HTTPException(status_code=404)

    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{file_path}")
        return Response(content=r.content, media_type=r.headers.get("content-type"))

@router.post("/use-in-deal/{deal_id}")
async def use_template_for_deal(deal_id: str, payload: UseTemplateIn, user=CurrentUser, db: Session = Depends(get_db)):
    deal_obj = db.query(Deal).filter(Deal.id == deal_id, Deal.advertiser_id == user.id, Deal.status == DealStatus.creative_draft.value).one_or_none()
    if not deal_obj: raise HTTPException(status_code=404)
    tpl = db.query(PostTemplate).filter(PostTemplate.id == payload.template_id, PostTemplate.owner_id == user.id).one_or_none()
    if not tpl or not tpl.creative_message_ids: raise HTTPException(status_code=404)

    deal_obj.creative_chat_id = str(tpl.creative_chat_id)
    deal_obj.creative_message_ids = tpl.creative_message_ids
    deal_obj.creative_type = tpl.creative_type or "template"
    deal_obj.creative_preview_text = tpl.preview_text or ""
    deal_obj.creative_preview_file_id = tpl.preview_file_id or ""
    deal_obj.creative_preview_file_ids = tpl.preview_file_ids or ""
    deal_obj.creative_preview_count = tpl.preview_count
    db.commit()
    return {"ok": True}
