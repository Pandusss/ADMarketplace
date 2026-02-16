"""
Incoming bot-chat message handler.
Relays messages between deal participants,
accepts creatives (photo/video/document/album), manages post templates.
"""
from __future__ import annotations
import asyncio
import json
import time
import logging
from datetime import datetime
from typing import Any, Final, Optional

from sqlalchemy.orm import Session
from app.infra.telegram.bot_client import TelegramBotClient
from app.domain.chat.service import ChatService
from app.db.models.deal import Deal, DealStatus
from app.db.models.channel import Channel
from app.db.models.post_template import PostTemplate
from app.db.models.user_chat_context import ChatInputMode

logger = logging.getLogger(__name__)

# Constants
CREATIVE_TYPE_PHOTO: Final[str] = "photo"
CREATIVE_TYPE_VIDEO: Final[str] = "video"
CREATIVE_TYPE_DOCUMENT: Final[str] = "document"
CREATIVE_TYPE_VOICE: Final[str] = "voice"
CREATIVE_TYPE_ALBUM: Final[str] = "album"
CREATIVE_TYPE_TEXT: Final[str] = "text"

CONTEXT_TEMPLATE: Final[str] = "template"
CONTEXT_DEAL: Final[str] = "deal"

MSG_TEMPLATE_SAVED: Final[str] = "✅ Template '{title}' saved."
MSG_TEMPLATE_SAVED_ALBUM: Final[str] = "✅ Template '{title}' saved (Album)."
MSG_DEAL_SAVED_CONFIRM: Final[str] = "Above is your creative for deal #{deal_id}. Is this correct?"
MSG_DEAL_ALBUM_RECEIVED: Final[str] = "✅ Album for deal #{deal_id} received. Confirm submission below."
MSG_ALBUM_RECEIVING: Final[str] = "📎 Album received. Saving {label}… ({count})"
MSG_CLOSED_DEAL: Final[str] = "🛑 Deal #{deal_id} is closed. No other active chats."
MSG_SWITCHED_DEAL: Final[str] = "⚠️ Deal #{old_id} was closed. Switched to Deal #{new_id}."
MSG_SELECT_DEAL: Final[str] = "⚠️ Deal #{old_id} was closed. Select another chat:"
MSG_MULTIPLE_DEALS: Final[str] = "🔢 You have multiple active deals. Please select one to chat:"
MSG_NEW_MESSAGE_OTHER: Final[str] = "📨 <b>New message in other deal</b> {emoji}\nOpen chats list to switch."

class MediaGroupBuffer:
    """
    Manages state for Telegram Media Groups (albums).
    Since updates come individually, we buffer them for a short time to aggregate.
    """
    _groups: dict[tuple[int, str], dict[str, Any]] = {}
    _lock = asyncio.Lock()
    TIMEOUT: float = 2.0

    @classmethod
    async def add_message(cls, user_id: int, mg_id: str, chat_id: str, message: dict, handler: 'ChatHandler', **kwargs):
        key = (user_id, mg_id)
        async with cls._lock:
            buf = cls._groups.get(key)
            if not buf:
                # Initialize buffer
                ptxt, pfile, _ = ChatHandler.extract_preview_snapshot(message)
                buf = {
                    "chat_id": chat_id,
                    "message_ids": [],
                    "preview_text": ptxt,
                    "preview_file_id": pfile,
                    "preview_file_ids": [pfile] if pfile else [],
                    "first_ts": time.monotonic(),
                    "status_message_id": None,
                    "handler_ref": handler, # To call back for finalization (be careful with circular refs/gc, but short lived)
                    **kwargs
                }
                cls._groups[key] = buf
                asyncio.create_task(cls._finalize_task(key))
            
            # Update buffer
            msg_id = message.get("message_id")
            if msg_id:
                buf["message_ids"].append(int(msg_id))
            
            _, pfile, _ = ChatHandler.extract_preview_snapshot(message)
            if pfile:
                buf.setdefault("preview_file_ids", []).append(pfile)
            
            # Notify user about progress
            await cls._update_status_message(handler.bot, chat_id, buf)

    @classmethod
    async def _update_status_message(cls, bot: TelegramBotClient, chat_id: str, buf: dict):
        count = len(buf["message_ids"])
        label = "template" if buf.get("kind") == CONTEXT_TEMPLATE else "creative"
        text = MSG_ALBUM_RECEIVING.format(label=label, count=count)
        
        try:
            if buf["status_message_id"]:
                await bot.edit_message_text(chat_id=chat_id, message_id=buf["status_message_id"], text=text)
            else:
                msg = await bot.send_message(chat_id, text)
                buf["status_message_id"] = int(msg["message_id"])
        except Exception:
            pass # Ignore edit errors

    @classmethod
    async def _finalize_task(cls, key: tuple[int, str]):
        await asyncio.sleep(cls.TIMEOUT)
        async with cls._lock:
            buf = cls._groups.pop(key, None)
            if not buf: return
        
        # We need a fresh DB session here because this runs in background
        from app.core.database import SessionLocal
        with SessionLocal() as db:
            handler = buf["handler_ref"] 
            await ChatHandler.process_album_finalization(db, handler.bot, buf)


class ChatHandler:
    def __init__(self, bot: TelegramBotClient, db: Session):
        self.bot = bot
        self.db = db
        self.chat_service = ChatService(db)

    @staticmethod
    def detect_creative_type(message: dict) -> str:
        if message.get("media_group_id"): return CREATIVE_TYPE_ALBUM
        return ChatService.detect_content_type(message)

    @staticmethod
    def extract_preview_snapshot(message: dict) -> tuple[str, str | None, int]:
        text = message.get("caption") or message.get("text") or ""
        file_id = None
        count = 0
        if message.get("photo"):
            file_id = message["photo"][-1]["file_id"]
            count = 1
        elif message.get("video"):
            file_id = message["video"]["file_id"]
            count = 1
        return text, file_id, count

    async def handle_message(self, message: dict) -> bool:
        chat_id = str(message.get("chat", {}).get("id"))
        from_user = message.get("from") or {}
        user_id = from_user.get("id")
        uid = f"tg_{user_id}"
        
        # 1. Template Intake
        if await self._handle_template_intake(chat_id, user_id, uid, message):
            return True

        # 2. Deal Creative Submission
        if await self._handle_deal_submission(chat_id, user_id, uid, message):
            return True

        # 3. Chat Relay
        return await self._handle_chat_relay(chat_id, uid, message)

    async def _handle_template_intake(self, chat_id: str, user_id: int, uid: str, message: dict) -> bool:
        waiting_tpl = (
            self.db.query(PostTemplate)
            .filter(PostTemplate.owner_id == uid, PostTemplate.waiting_for_content == True)
            .order_by(PostTemplate.updated_at.desc())
            .first()
        )
        if not waiting_tpl:
            return False

        media_group_id = message.get("media_group_id")
        if media_group_id:
            await MediaGroupBuffer.add_message(
                user_id, f"tpl:{media_group_id}", chat_id, message, self, 
                kind=CONTEXT_TEMPLATE, template_id=waiting_tpl.id
            )
            return True

        msg_id = message.get("message_id")
        if not msg_id:
            return True

        # Save single message
        ptxt, pfile, _ = self.extract_preview_snapshot(message)
        self._save_creative_to_db(
            db=self.db,
            obj=waiting_tpl,
            chat_id=chat_id,
            message_ids=[int(msg_id)],
            creative_type=self.detect_creative_type(message),
            preview_text=ptxt,
            preview_file_id=pfile,
            preview_file_ids=[pfile] if pfile else [],
            count=1
        )
        await self.bot.send_message(chat_id, MSG_TEMPLATE_SAVED.format(title=waiting_tpl.title))
        return True

    async def _handle_deal_submission(self, chat_id: str, user_id: int, uid: str, message: dict) -> bool:
        # Find relevant deal
        deal_obj = (
            self.db.query(Deal)
            .join(Channel, Channel.id == Deal.channel_id)
            .filter(Deal.status == DealStatus.creative_draft.value, Deal.waiting_for_creative == True)
            .filter(
                ((Deal.advertiser_id == uid) & ((Deal.creative_mode == None) | (Deal.creative_mode == "template"))) |
                ((Channel.owner_id == uid) & (Deal.creative_mode == "custom_task"))
            )
            .order_by(Deal.updated_at.desc())
            .first()
        )
        if not deal_obj:
            return False

        media_group_id = message.get("media_group_id")
        if media_group_id:
            await MediaGroupBuffer.add_message(
                user_id, str(media_group_id), chat_id, message, self, 
                kind=CONTEXT_DEAL, deal_id=deal_obj.id
            )
            return True

        msg_id = message.get("message_id")
        if not msg_id:
            return True

        # Save single message
        ptxt, pfile, _ = self.extract_preview_snapshot(message)
        self._save_creative_to_db(
            db=self.db,
            obj=deal_obj,
            chat_id=chat_id,
            message_ids=[int(msg_id)],
            creative_type=self.detect_creative_type(message),
            preview_text=ptxt,
            preview_file_id=pfile,
            preview_file_ids=[pfile] if pfile else [],
            count=1
        )

        await self.bot.copy_message(chat_id=chat_id, from_chat_id=chat_id, message_id=int(msg_id))
        
        kb = {"inline_keyboard": [[
            {"text": "✅ Confirm & Submit", "callback_data": f"conf_deal_{deal_obj.id}"},
            {"text": "❌ Edit / Cancel", "callback_data": f"cancel_deal_{deal_obj.id}"}
        ]]}
        await self.bot.send_message(chat_id, MSG_DEAL_SAVED_CONFIRM.format(deal_id=deal_obj.id), reply_markup=kb)
        return True

    @staticmethod
    def _save_creative_to_db(
        db: Session, obj: Any, chat_id: str, message_ids: list[int], 
        creative_type: str, preview_text: str, preview_file_id: str | None, 
        preview_file_ids: list[str], count: int
    ):
        """Unified method to save creative content to either PostTemplate or Deal."""
        # Mapping for Deal object (uses distinct field names)
        if hasattr(obj, 'creative_preview_text'): 
            obj.creative_chat_id = chat_id
            obj.creative_message_ids = json.dumps(message_ids)
            obj.creative_type = creative_type
            obj.creative_preview_text = preview_text or ""
            obj.creative_preview_file_id = preview_file_id or ""
            obj.creative_preview_file_ids = json.dumps(preview_file_ids) if preview_file_ids else "[]"
            obj.creative_preview_count = count
        # Mapping for PostTemplate object
        else:
            obj.creative_chat_id = chat_id
            obj.creative_message_ids = json.dumps(message_ids)
            obj.creative_type = creative_type
            obj.preview_text = preview_text or ""
            obj.preview_file_id = preview_file_id or ""
            obj.preview_file_ids = json.dumps(preview_file_ids) if preview_file_ids else "[]"
            obj.preview_count = count
            obj.waiting_for_content = False
            obj.updated_at = datetime.utcnow()
        
        db.commit()

    @staticmethod
    async def process_album_finalization(db: Session, bot: TelegramBotClient, buf: dict):
        """Processes the finalized album buffer and saves to DB."""
        chat_id = buf["chat_id"]
        kind = buf.get("kind")
        
        obj = None
        if kind == CONTEXT_TEMPLATE:
            obj = db.query(PostTemplate).get(buf["template_id"])
        elif kind == CONTEXT_DEAL:
            obj = db.query(Deal).get(buf["deal_id"])
            
        if not obj:
            return

        ChatHandler._save_creative_to_db(
            db=db,
            obj=obj,
            chat_id=chat_id,
            message_ids=buf["message_ids"],
            creative_type=CREATIVE_TYPE_ALBUM,
            preview_text=buf["preview_text"],
            preview_file_id=buf["preview_file_id"],
            preview_file_ids=buf["preview_file_ids"],
            count=len(buf["message_ids"])
        )

        if kind == CONTEXT_TEMPLATE:
            await bot.send_message(chat_id, MSG_TEMPLATE_SAVED_ALBUM.format(title=obj.title))
        elif kind == CONTEXT_DEAL:
            kb = {"inline_keyboard": [[{"text": "✅ Confirm", "callback_data": f"conf_deal_{obj.id}"}]]}
            await bot.send_message(chat_id, MSG_DEAL_ALBUM_RECEIVED.format(deal_id=obj.id), reply_markup=kb)

    async def _handle_chat_relay(self, chat_id: str, uid: str, message: dict) -> bool:
        ctx = self.chat_service.get_user_context(uid)
        
        if not ctx:
            active_deals = self.chat_service.get_active_deals(uid)
            if not active_deals:
                return True
            
            if len(active_deals) == 1:
                deal = active_deals[0]
                self.chat_service.set_user_context(uid, deal.id, ChatInputMode.CHAT)
                ctx = self.chat_service.get_user_context(uid)
            else:
                kb = {"inline_keyboard": [[{"text": f"Deal #{d.id}", "callback_data": f"select_deal_{d.id}"}] for d in active_deals]}
                await self.bot.send_message(chat_id, MSG_MULTIPLE_DEALS, reply_markup=kb)
                return True

        deal = self.db.query(Deal).get(ctx.deal_id)
        if not deal:
            self.chat_service.clear_user_context(uid)
            return True

        if deal.status in [DealStatus.released.value, DealStatus.cancelled.value, DealStatus.refunded.value]:
            return await self._handle_closed_chat(chat_id, uid, deal)

        if ctx.input_mode == ChatInputMode.CHAT.value:
            result = await self.chat_service.relay_chat_message(self.bot, uid, deal.id, message)
            if isinstance(result, dict) and result.get("should_notify_cross_chat"):
                await self._send_cross_chat_notification(
                    result["recipient_tg_id"], result["deal_emoji"], result["recipient_id"], deal.id
                )
        
        return True

    async def _handle_closed_chat(self, chat_id: str, uid: str, old_deal: Deal) -> bool:
        self.chat_service.clear_user_context(uid)
        active_deals = self.chat_service.get_active_deals(uid)
        
        if not active_deals:
            await self.bot.send_message(chat_id, MSG_CLOSED_DEAL.format(deal_id=old_deal.id))
            return True
        
        if len(active_deals) == 1:
            new_deal = active_deals[0]
            self.chat_service.set_user_context(uid, new_deal.id, ChatInputMode.CHAT)
            await self.bot.send_message(chat_id, MSG_SWITCHED_DEAL.format(old_id=old_deal.id, new_id=new_deal.id), parse_mode="HTML")
            return True
        else:
            kb = {"inline_keyboard": [[{"text": f"Deal #{d.id}", "callback_data": f"select_deal_{d.id}"}] for d in active_deals]}
            await self.bot.send_message(chat_id, MSG_SELECT_DEAL.format(old_id=old_deal.id), reply_markup=kb)
            return True

    async def _send_cross_chat_notification(self, tg_id: str, emoji: str, recipient_db_id: str, deal_id: str):
        kb = {"inline_keyboard": [[{"text": "📂 Open Chats", "callback_data": "open_chats_list"}]]}
        text = MSG_NEW_MESSAGE_OTHER.format(emoji=emoji)
        await self.bot.send_message(tg_id, text, parse_mode="HTML", reply_markup=kb)
        self.chat_service.mark_cross_chat_notified(recipient_db_id, deal_id)
