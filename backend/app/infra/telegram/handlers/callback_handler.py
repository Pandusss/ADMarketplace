"""
Telegram bot inline-button (callback_query) handler.
Creative confirm/cancel, chat and deal selection,
opening the chats list.
"""
from __future__ import annotations
import logging
from typing import Final

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.infra.telegram.bot_client import TelegramBotClient
from app.domain.chat.service import ChatService
from app.db.models.deal import Deal
from app.db.models.channel import Channel
from app.db.models.user_chat_context import ChatInputMode
from app.domain.deals.service import submit_creative_action

logger = logging.getLogger(__name__)

# Constants
CB_CONFIRM_DEAL: Final[str] = "conf_deal_"
CB_CANCEL_DEAL: Final[str] = "cancel_deal_"
CB_SELECT_CHAT: Final[str] = "select_chat_"
CB_SELECT_DEAL: Final[str] = "select_deal_"
ACTION_OPEN_CHATS: Final[str] = "open_chats_list"

MSG_SUBMITTED: Final[str] = "✅ Submitted!"
MSG_SUBMITTED_TEXT: Final[str] = "✅ Creative for deal #{deal_id} submitted."
MSG_CANCELLED: Final[str] = "Cancelled."
MSG_CANCELLED_TEXT: Final[str] = "❌ Submission cancelled. You can send a new post."
MSG_DEAL_NOT_FOUND: Final[str] = "❌ Deal not found"
MSG_ACCESS_DENIED: Final[str] = "❌ Access denied"
MSG_CHAT_SELECTED: Final[str] = "✅ Chat selected"
MSG_CHATS_LIST: Final[str] = "📂 List of chats"
MSG_ERROR_PROCESSING: Final[str] = "❌ Error processing request"

ROLE_SELLER: Final[str] = "Seller"
ROLE_BUYER: Final[str] = "Buyer"

from typing import TypedDict, Optional, Dict, Any

class CallbackQuery(TypedDict):
    id: str
    data: Optional[str]
    message: Dict[str, Any]
    from_user: Dict[str, Any] # 'from' in API, but using alias or direct dict access

class CallbackHandler:
    def __init__(self, bot: TelegramBotClient, db: Session):
        self.bot = bot
        self.db = db
        self.chat_service = ChatService(db)
        
        # Dispatch Map
        self.handlers = {
            CB_CONFIRM_DEAL: self._handle_conf_deal,
            CB_CANCEL_DEAL: self._handle_cancel_deal,
            CB_SELECT_CHAT: self._handle_select_chat,
            CB_SELECT_DEAL: self._handle_select_chat, # Same handler
            ACTION_OPEN_CHATS: self._handle_open_chats,
        }

    async def handle_callback(self, callback_query: Dict[str, Any]) -> bool:
        data = str(callback_query.get("data") or "")
        chat_id = str(callback_query.get("message", {}).get("chat", {}).get("id"))
        from_user = callback_query.get("from") or {}
        user_id = from_user.get("id")
        uid = f"tg_{user_id}"
        cb_id = callback_query["id"]
        msg_id = callback_query.get("message", {}).get("message_id")

        try:
            # Match handler by prefix
            for prefix, handler in self.handlers.items():
                if data.startswith(prefix) or data == prefix:
                    return await handler(cb_id=cb_id, chat_id=chat_id, msg_id=msg_id, uid=uid, data=data)
            
            logger.debug(f"Unhandled callback data: {data}")
            return False
            
        except Exception as e:
            logger.error(f"Error handling callback {data}: {e}", exc_info=True)
            await self.bot.answer_callback_query(cb_id, MSG_ERROR_PROCESSING)
            return True

    async def _handle_conf_deal(self, cb_id: str, chat_id: str, msg_id: int, uid: str, data: str) -> bool:
        deal_id = data.removeprefix(CB_CONFIRM_DEAL)
        try:
            await submit_creative_action(self.db, deal_id, uid)
            await self.bot.answer_callback_query(cb_id, MSG_SUBMITTED)
            if msg_id:
                try:
                    await self.bot.edit_message_text(
                        chat_id=chat_id, 
                        message_id=msg_id, 
                        text=MSG_SUBMITTED_TEXT.format(deal_id=deal_id)
                    )
                except Exception:
                    pass # Message might be too old or deleted
        except HTTPException as e:
            await self.bot.answer_callback_query(cb_id, f"❌ {e.detail}")
        return True

    async def _handle_cancel_deal(self, cb_id: str, chat_id: str, msg_id: int, uid: str, data: str) -> bool:
        await self.bot.answer_callback_query(cb_id, MSG_CANCELLED)
        if msg_id:
            try:
                await self.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=MSG_CANCELLED_TEXT)
            except Exception:
                pass
        return True

    async def _handle_select_chat(self, cb_id: str, chat_id: str, msg_id: int, uid: str, data: str) -> bool:
        # Determine deal_id based on prefix
        if data.startswith(CB_SELECT_CHAT):
            deal_id = data.removeprefix(CB_SELECT_CHAT)
        elif data.startswith(CB_SELECT_DEAL):
            deal_id = data.removeprefix(CB_SELECT_DEAL)
        else:
            return False
        
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            await self.bot.answer_callback_query(cb_id, MSG_DEAL_NOT_FOUND)
            return True
        
        channel = self.db.query(Channel).get(deal.channel_id)
        
        # Determine role
        other_role = None
        if uid == deal.advertiser_id:
            other_role = ROLE_SELLER
        elif channel and uid == channel.owner_id:
            other_role = ROLE_BUYER
        
        if not other_role:
            await self.bot.answer_callback_query(cb_id, MSG_ACCESS_DENIED)
            return True
            
        unread_messages = self.chat_service.get_unread_messages_from_other_party(uid, deal_id)
        self.chat_service.set_user_context(uid, deal_id, ChatInputMode.CHAT)
        self.chat_service.mark_as_read(uid, deal_id)
        
        await self.bot.answer_callback_query(cb_id, MSG_CHAT_SELECTED)
        
        await self._send_chat_history(chat_id, deal, other_role, unread_messages)
        return True

    async def _handle_open_chats(self, cb_id: str, chat_id: str, msg_id: int, uid: str, data: str) -> bool:
        ctx = self.chat_service.get_user_context(uid)
        active_deal_id = ctx.deal_id if ctx else None
        
        try:
            message_text, keyboard = self.chat_service.format_chat_list(uid, active_deal_id)
            
            await self.bot.answer_callback_query(cb_id, MSG_CHATS_LIST)
            
            kwargs = {"parse_mode": "HTML"}
            if keyboard and keyboard.get("inline_keyboard"):
                kwargs["reply_markup"] = keyboard
                
            await self.bot.send_message(chat_id, message_text, **kwargs)
        except Exception:
            await self.bot.answer_callback_query(cb_id, MSG_ERROR_PROCESSING)
            
        return True

    async def _send_chat_history(self, chat_id: str, deal: Deal, other_role: str, unread_messages: list):
        """Sends unread messages to the user or a welcome message if no new messages."""
        if unread_messages:
            await self.bot.send_message(chat_id, f"💬 <b>New messages in {deal.emoji} Deal #{deal.id}:</b>", parse_mode="HTML")
            for msg in unread_messages:
                timestamp = msg.created_at.strftime("%d.%m %H:%M")
                content = msg.content_text if msg.content_text else f"[{msg.content_type}]"
                await self.bot.send_message(
                    chat_id, 
                    f"<b>[{timestamp}] {other_role}:</b>\n{content}", 
                    parse_mode="HTML"
                )
            await self.bot.send_message(
                chat_id, 
                f"\n✅ <b>You are now in {deal.emoji} Deal #{deal.id}</b>\nSend a message to reply.", 
                parse_mode="HTML"
            )
        else:
            await self.bot.send_message(
                chat_id, 
                f"💬 <b>You are now chatting in {deal.emoji} Deal #{deal.id}</b>\n\nNo new messages. Send a message to continue the conversation.", 
                parse_mode="HTML"
            )
