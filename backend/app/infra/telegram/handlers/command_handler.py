"""
Telegram bot command handler (/start, /chats and deep-linking).
Creative preview, deal chat subscription,
template navigation.
"""
from __future__ import annotations
import json
import logging
from typing import Final

from sqlalchemy.orm import Session
from app.infra.telegram.bot_client import TelegramBotClient
from app.domain.chat.service import ChatService
from app.db.models.deal import Deal
from app.db.models.channel import Channel
from app.db.models.post_template import PostTemplate
from app.db.models.user_chat_context import ChatInputMode

logger = logging.getLogger(__name__)

# Prefixes for deep linking
PREFIX_SUB: Final[str] = "sub_"
PREFIX_DEAL: Final[str] = "deal_"
PREFIX_TPL: Final[str] = "tplview_"

# Messages
MSG_START_WELCOME: Final[str] = "Welcome to the AdMarketplace Bot! Use the Mini App to manage your campaigns and channels."
MSG_DEAL_NOT_FOUND: Final[str] = "Deal not found."
MSG_ACCESS_DENIED: Final[str] = "Access denied."
MSG_UNAUTHORIZED_SUBMISSION: Final[str] = "You are not authorized to submit a creative for this deal."
MSG_NO_CREATIVE: Final[str] = "No creative submitted yet."
MSG_PREVIEW_SENT: Final[str] = "✅ Preview sent above. Return to Mini App to approve/reject."
MSG_PREVIEW_ERROR: Final[str] = "❌ Error loading preview."
MSG_TEMPLATE_NOT_FOUND: Final[str] = "Template not found."
MSG_TEMPLATE_EMPTY: Final[str] = "Template is empty. Create it first."
MSG_TEMPLATE_SENT: Final[str] = "✅ Template preview sent."
MSG_TEMPLATE_ERROR: Final[str] = "❌ Error loading template preview."
MSG_SUBMISSION_INSTRUCTIONS: Final[str] = (
    "📝 Deal #{deal_id} selected for CREATIVE SUBMISSION.\n\n"
    "Please send the post now (text, photo, or album). It will be sent to the {target} for approval."
)

class CommandHandler:
    def __init__(self, bot: TelegramBotClient, db: Session):
        self.bot = bot
        self.db = db
        self.chat_service = ChatService(db)
        # Dispatch map for deep links
        self.start_handlers = {
            PREFIX_SUB: self._handle_sub_link,
            PREFIX_DEAL: self._handle_deal_link,
            PREFIX_TPL: self._handle_tpl_view_link,
        }

    async def handle_start(self, chat_id: str, user_id: int, text: str) -> bool:
        """
        Handles the /start command, potentially with a payload (deep linking).
        """
        parts = text.split(maxsplit=1)
        payload = parts[1].strip() if len(parts) == 2 else ""
        
        if not payload:
            await self.bot.send_message(chat_id, MSG_START_WELCOME, parse_mode="HTML")
            return True

        uid = f"tg_{user_id}"
        
        # Determine handler based on prefix
        for prefix, handler in self.start_handlers.items():
            if payload.startswith(prefix):
                try:
                    return await handler(chat_id, uid, payload)
                except Exception as e:
                    logger.error(f"Error handling deep link '{payload}': {e}", exc_info=True)
                    await self.bot.send_message(chat_id, "❌ An error occurred processing this link.")
                    return True

        # Unknown payload, treat as normal start
        logger.info(f"Unknown start payload from {user_id}: {payload}")
        await self.bot.send_message(chat_id, MSG_START_WELCOME, parse_mode="HTML")
        return True

    async def handle_chats(self, chat_id: str, user_id: int) -> bool:
        uid = f"tg_{user_id}"
        
        try:
            # Check context
            ctx = self.chat_service.get_user_context(uid)
            active_deal_id = ctx.deal_id if ctx else None
            
            message_text, keyboard = self.chat_service.format_chat_list(uid, active_deal_id)
            
            kwargs = {"parse_mode": "HTML"}
            if keyboard and keyboard.get("inline_keyboard"):
                kwargs["reply_markup"] = keyboard
                
            await self.bot.send_message(chat_id, message_text, **kwargs)
            return True
        except Exception as e:
            logger.error(f"Error handling /chats for {user_id}: {e}", exc_info=True)
            await self.bot.send_message(chat_id, "❌ Could not load chats.")
            return True

    async def _handle_sub_link(self, chat_id: str, uid: str, payload: str) -> bool:
        deal_id = payload.removeprefix(PREFIX_SUB)
        deal_obj = self.db.query(Deal).filter(Deal.id == deal_id).one_or_none()
        
        if not deal_obj:
            await self.bot.send_message(chat_id, MSG_DEAL_NOT_FOUND)
            return True
        
        channel = self.db.query(Channel).filter(Channel.id == deal_obj.channel_id).one_or_none()
        creative_mode = deal_obj.creative_mode or "template"
        
        # Check permissions
        is_advertiser = (deal_obj.advertiser_id == uid)
        is_owner = (channel and channel.owner_id == uid)
        
        can_submit = (is_advertiser and creative_mode == "template") or \
                     (is_owner and creative_mode == "custom_task")
        
        if not can_submit:
            await self.bot.send_message(chat_id, MSG_UNAUTHORIZED_SUBMISSION)
            return True
        
        # Set context
        self.chat_service.set_user_context(uid, deal_obj.id, ChatInputMode.CREATIVE_SUBMISSION)
        
        # Mark deal as waiting (redundant if handled elsewhere, but safe)
        if hasattr(deal_obj, 'waiting_for_creative'):
             deal_obj.waiting_for_creative = True
             self.db.commit()
        
        target = "channel" if creative_mode == "template" else "advertiser"
        msg = MSG_SUBMISSION_INSTRUCTIONS.format(deal_id=deal_id, target=target)
        await self.bot.send_message(chat_id, msg)
        return True

    async def _handle_deal_link(self, chat_id: str, uid: str, payload: str) -> bool:
        deal_id = payload.removeprefix(PREFIX_DEAL)
        deal_obj = self.db.query(Deal).filter(Deal.id == deal_id).one_or_none()
        
        if not deal_obj:
            await self.bot.send_message(chat_id, MSG_DEAL_NOT_FOUND)
            return True
        
        channel = self.db.query(Channel).filter(Channel.id == deal_obj.channel_id).one_or_none()
        
        # Access control
        if not (deal_obj.advertiser_id == uid or (channel and channel.owner_id == uid)):
            await self.bot.send_message(chat_id, MSG_ACCESS_DENIED)
            return True
            
        if not deal_obj.creative_chat_id or not deal_obj.creative_message_ids:
            await self.bot.send_message(chat_id, MSG_NO_CREATIVE)
            return True
            
        await self._send_message_preview(
            chat_id=chat_id,
            from_chat_id=str(deal_obj.creative_chat_id),
            message_ids_json=deal_obj.creative_message_ids,
            success_msg=MSG_PREVIEW_SENT,
            error_msg=MSG_PREVIEW_ERROR
        )
        return True

    async def _handle_tpl_view_link(self, chat_id: str, uid: str, payload: str) -> bool:
        tpl_id = payload.removeprefix(PREFIX_TPL)
        tpl = self.db.query(PostTemplate).filter(PostTemplate.id == tpl_id).one_or_none()
        
        if not tpl or tpl.owner_id != uid:
            await self.bot.send_message(chat_id, MSG_TEMPLATE_NOT_FOUND)
            return True
            
        if not tpl.creative_chat_id or not tpl.creative_message_ids:
            await self.bot.send_message(chat_id, MSG_TEMPLATE_EMPTY)
            return True
            
        await self._send_message_preview(
            chat_id=chat_id,
            from_chat_id=str(tpl.creative_chat_id),
            message_ids_json=tpl.creative_message_ids,
            success_msg=MSG_TEMPLATE_SENT,
            error_msg=MSG_TEMPLATE_ERROR
        )
        return True

    async def _send_message_preview(
        self, 
        chat_id: str, 
        from_chat_id: str, 
        message_ids_json: str | None, 
        success_msg: str, 
        error_msg: str
    ):
        """Helper to parse JSON message IDs and copy them to the user."""
        try:
            message_ids = json.loads(message_ids_json or "[]")
            if not message_ids:
                raise ValueError("Empty message_ids")
                
            # Telethon copy_messages usually returns the new messages, but we just await completion
            await self.bot.copy_messages(
                chat_id=chat_id, 
                from_chat_id=from_chat_id, 
                message_ids=[int(x) for x in message_ids]
            )
            await self.bot.send_message(chat_id, success_msg)
        except Exception as e:
            logger.error(f"Preview error (copy_messages): {e}") # Standard error log
            await self.bot.send_message(chat_id, error_msg)
