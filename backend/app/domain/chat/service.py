"""
Chat Domain Service.
Manages real-time communication between deal participants, 
including message persistence, AI assistance integration, and notification triggers.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.channel import Channel
from app.db.models.chat_message import ChatMessage
from app.db.models.chat_unread_count import ChatUnreadCount
from app.db.models.deal import Deal, DealStatus
from app.db.models.user import User
from app.db.models.user_chat_context import UserChatContext, ChatInputMode
from app.infra.telegram.bot_client import TelegramBotClient
from app.infra.redis.service import redis_service

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MESSAGE_LIMIT = 100

class ChatService:
    def __init__(self, db: Session):
        self.db = db
        self.redis = redis_service

    def get_user_context(self, user_id: str) -> UserChatContext | None:
        """
        Get user chat context. 
        Tries Redis first, falls back to database.
        """
        # Try Redis first
        redis_ctx = self.redis.get_user_context(user_id)
        if redis_ctx:
            # Convert Redis data to UserChatContext-like object
            ctx = UserChatContext(
                user_id=user_id,
                deal_id=redis_ctx["deal_id"],
                input_mode=redis_ctx["input_mode"]
            )
            return ctx
        
        # Fallback to database
        ctx = self.db.query(UserChatContext).filter(UserChatContext.user_id == user_id).first()
        if ctx:
            # Restore to Redis
            self.redis.set_user_context(user_id, ctx.deal_id, ctx.input_mode)
        
        return ctx

    def set_user_context(self, user_id: str, deal_id: str, mode: ChatInputMode = ChatInputMode.CHAT) -> None:
        """
        Set user chat context.
        Writes to both Redis (fast) and database (reliable backup).
        """
        ok = self.redis.set_user_context(user_id, deal_id, mode.value)
        if not ok:
            logger.warning("Redis context set failed, DB-only fallback", extra={"user_id": user_id, "deal_id": deal_id})
        
        ctx = self.db.query(UserChatContext).filter(UserChatContext.user_id == user_id).first()
        if not ctx:
            ctx = UserChatContext(user_id=user_id, deal_id=deal_id, input_mode=mode.value)
            self.db.add(ctx)
        else:
            ctx.deal_id = deal_id
            ctx.input_mode = mode.value
        self.db.commit()

    def clear_user_context(self, user_id: str) -> None:
        """
        Clear user chat context from both Redis and database.
        """
        # Clear from Redis
        self.redis.clear_user_context(user_id)
        
        # Clear from database
        ctx = self.db.query(UserChatContext).filter(UserChatContext.user_id == user_id).first()
        if ctx:
            self.db.delete(ctx)
            self.db.commit()

    def clear_deal_context(self, deal_id: str) -> None:
        """
        Clears chat context for any user associated with this deal.
        """
        self.db.query(UserChatContext).filter(UserChatContext.deal_id == deal_id).delete()
        self.db.commit()

    def get_active_deals(self, user_id: str) -> list[Deal]:
        """
        Returns active deals for a user (either as advertiser or channel owner).
        Excludes finalized/cancelled states.
        """
        # Find owned channel IDs first
        owned_channels = self.db.query(Channel.id).filter(Channel.owner_id == user_id).all()
        channel_ids = [c[0] for c in owned_channels]

        # Build list of excluded statuses
        excluded_statuses = [
            DealStatus.released.value,
            DealStatus.cancelled.value,
            DealStatus.refunded.value,
        ]
        
        # Add optional statuses if they exist
        if hasattr(DealStatus, "completed"):
            excluded_statuses.append(DealStatus.completed.value)
        if hasattr(DealStatus, "disputed"):
            excluded_statuses.append(DealStatus.disputed.value)

        return self.db.query(Deal).filter(
            or_(Deal.advertiser_id == user_id, Deal.channel_id.in_(channel_ids))
        ).filter(
            Deal.status.notin_(excluded_statuses)
        ).all()

    def get_unread_counts(self, user_id: str) -> dict[str, int]:
        """
        Returns a dictionary mapping deal_id -> unread_count for all deals.
        Tries Redis first, falls back to database.
        """
        # Try Redis first
        counts = self.redis.get_all_unread_counts(user_id)
        if counts:
            return counts
        
        # Fallback to database
        db_counts = self.db.query(ChatUnreadCount).filter(ChatUnreadCount.user_id == user_id).all()
        return {c.deal_id: c.unread_count for c in db_counts}

    def increment_unread(self, user_id: str, deal_id: str) -> None:
        """
        Increments the unread count for a user-deal pair.
        Uses Redis only (no database writes).
        """
        # Write to Redis only
        self.redis.increment_unread(user_id, deal_id)

    def mark_as_read(self, user_id: str, deal_id: str) -> None:
        """
        Marks all messages as read for a user-deal pair.
        Uses Redis only (no database writes).
        """
        # Write to Redis only
        self.redis.mark_as_read(user_id, deal_id)

    def update_last_read_timestamp(self, user_id: str, deal_id: str) -> None:
        """
        Updates last_read_at timestamp when a message is delivered in real-time
        (user is in active chat). This ensures that messages delivered directly
        are not shown again when user switches back to this chat.
        """
        # Write to Redis only
        self.redis.update_last_read_timestamp(user_id, deal_id)

    def should_send_cross_chat_notification(self, user_id: str, deal_id: str) -> bool:
        """
        Checks if cross-chat notification should be sent.
        Returns True only if there are unread messages and notification hasn't been sent yet.
        Uses Redis.
        """
        # Get from Redis
        unread_data = self.redis.get_unread_count(user_id, deal_id)
        if not unread_data:
            return False
        
        # Send notification only if there are unread messages and notification hasn't been sent
        return unread_data["count"] > 0 and unread_data["cross_chat_notified"] == 0
    
    def mark_cross_chat_notified(self, user_id: str, deal_id: str) -> None:
        """
        Marks that cross-chat notification has been sent for this deal.
        Uses Redis only.
        """
        # Write to Redis only
        self.redis.mark_cross_chat_notified(user_id, deal_id)

    def get_recent_messages(self, deal_id: str, limit: int = DEFAULT_MESSAGE_LIMIT) -> list[ChatMessage]:
        """
        Returns recent messages for a deal, ordered by creation time (oldest first).
        """
        return self.db.query(ChatMessage).filter(
            ChatMessage.deal_id == deal_id
        ).order_by(ChatMessage.created_at.asc()).limit(limit).all()

    def get_unread_messages_from_other_party(self, user_id: str, deal_id: str) -> list[ChatMessage]:
        """
        Returns only unread messages from the other party (not sent by user_id).
        Uses Redis to get last_read_at timestamp.
        """
        # Get the unread count record from Redis
        unread_data = self.redis.get_unread_count(user_id, deal_id)
        
        if not unread_data or unread_data["count"] == 0:
            return []
        
        count = unread_data["count"]
        
        # Get last N messages from other party
        # We rely on the count because last_read_at can be slightly off due to race conditions
        messages = self.db.query(ChatMessage).filter(
            ChatMessage.deal_id == deal_id,
            ChatMessage.sender_id != user_id,  # Only from other party
        ).order_by(ChatMessage.created_at.desc()).limit(count).all()
        
        # Return in chronological order
        return sorted(messages, key=lambda m: m.created_at)

    def format_chat_list(self, user_id: str, active_deal_id: str | None = None) -> tuple[str, dict]:
        """
        Formats the chat list message and inline keyboard for /chats command.
        Returns (message_text, inline_keyboard_dict)
        """
        deals = self.get_active_deals(user_id)
        if not deals:
            return ("You have no active deals.", {"inline_keyboard": []})
        
        unread_counts = self.get_unread_counts(user_id)
        
        message_lines = ["📂 Your active deals:", ""]
        keyboard_buttons = []
        
        for idx, deal in enumerate(deals, 1):
            unread = unread_counts.get(deal.id, 0)
            is_active = (deal.id == active_deal_id)
            
            # Format status indicator
            status_line = ""
            if unread > 0:
                status_line = f"   🔴 {unread} new message{'s' if unread != 1 else ''}"
            elif is_active:
                status_line = "   🟢 active chat"
            else:
                status_line = "   No new messages."
            
            message_lines.append(f"{idx}️⃣ #{deal.id} — {deal.emoji}")
            message_lines.append(status_line)
            message_lines.append("")
            
            # Add button
            button_text = f"{deal.emoji} #{deal.id}"
            if unread > 0:
                button_text += f" ({unread})" 
            elif is_active:
                button_text += " ✓"
            
            keyboard_buttons.append([{"text": button_text, "callback_data": f"select_chat_{deal.id}"}])
        
        message_text = "\n".join(message_lines)
        keyboard = {"inline_keyboard": keyboard_buttons}
        
        return (message_text, keyboard)

    @staticmethod
    def detect_content_type(message: dict) -> str:
        """
        Detect content type from Telegram message.
        
        Returns:
            Content type string: "text", "photo", "video", "document", "voice", "audio", "sticker", "animation"
        """
        if message.get("photo"): return "photo"
        if message.get("video"): return "video"
        if message.get("document"): return "document"
        if message.get("voice"): return "voice"
        if message.get("audio"): return "audio"
        if message.get("sticker"): return "sticker"
        if message.get("animation"): return "animation"
        return "text"

    def _resolve_recipient(self, deal: Deal, sender_id: str) -> tuple[str | None, str | None, str | None]:
        """
        Determines the recipient ID, their Telegram ID, and the sender's role name.
        """
        channel = self.db.query(Channel).get(deal.channel_id)
        if not channel or not channel.owner_id:
            return None, None, None

        if sender_id == deal.advertiser_id:
            recipient_id = channel.owner_id
            sender_role = "Buyer"
        elif sender_id == channel.owner_id:
            recipient_id = deal.advertiser_id
            sender_role = "Seller"
        else:
            return None, None, None

        recipient_user = self.db.query(User).get(recipient_id)
        if not recipient_user or not recipient_user.telegram_user_id:
            return None, None, None
            
        return recipient_id, str(recipient_user.telegram_user_id), sender_role

    async def _send_relayed_message(
        self, bot: TelegramBotClient, recipient_tg_id: str, message: dict, header: str
    ) -> bool:
        """
        Sends the relayed message to the recipient via Telegram.
        """
        msg_id = message.get("message_id")
        from_chat_id = message.get("chat", {}).get("id")
        text_content = message.get("text") or message.get("caption")

        merged_text = f"{header}\n{text_content}" if text_content else header
        
        try:
            if message.get("text"):
                # Plain text
                await bot.send_message(chat_id=recipient_tg_id, text=merged_text, parse_mode="HTML")
            else:
                # Media (Photo, Video, etc.)
                await bot.copy_message(
                    chat_id=recipient_tg_id, 
                    from_chat_id=from_chat_id, 
                    message_id=msg_id,
                    caption=merged_text,
                    parse_mode="HTML"
                )
            return True
        except Exception as e:
            logger.error(f"Failed to relay message to {recipient_tg_id}: {e}")
            return False

    def _save_chat_message(self, deal_id: str, sender_id: str, message: dict) -> None:
        """
        Saves the message to the database history.
        """
        msg_id = message.get("message_id")
        text_content = message.get("text") or message.get("caption")
        content_type = self.detect_content_type(message)

        chat_msg = ChatMessage(
            deal_id=deal_id,
            sender_id=sender_id,
            message_id=msg_id,
            content_text=text_content,
            content_type=content_type
        )
        self.db.add(chat_msg)
        self.db.commit()

    async def relay_chat_message(
        self, bot: TelegramBotClient, sender_id: str, deal_id: str, message: dict
    ) -> dict | None:
        """
        Relays a chat message to the other party.
        
        Returns:
            dict with relay info if successful, None if failed
        """
        deal = self.db.query(Deal).get(deal_id)
        if not deal:
            logger.warning(f"Deal not found", extra={"deal_id": deal_id})
            return None

        # 1. Resolve Recipient
        recipient_id, recipient_tg_id, sender_role = self._resolve_recipient(deal, sender_id)
        if not recipient_id or not recipient_tg_id:
            logger.warning(
                f"Could not resolve recipient for relay",
                extra={"deal_id": deal_id, "sender_id": sender_id}
            )
            return None

        # 2. Check context (is recipient in this chat?)
        recipient_ctx = self.get_user_context(recipient_id)
        recipient_in_this_chat = (recipient_ctx and recipient_ctx.deal_id == deal.id)
        recipient_in_other_chat = (recipient_ctx and recipient_ctx.deal_id != deal.id)
        recipient_has_no_context = (recipient_ctx is None)

        # 3. Relay Message (if recipient is in this chat OR has no context yet)
        if recipient_in_this_chat or recipient_has_no_context:
            header = f"<b>💬 {deal.emoji} Message from {sender_role} (#{deal.id}):</b>"
            success = await self._send_relayed_message(bot, recipient_tg_id, message, header)
            if success:
                logger.debug(f"Message relayed to {recipient_id} for deal {deal_id}")
                if recipient_in_this_chat:
                    self.update_last_read_timestamp(recipient_id, deal.id)
                elif recipient_has_no_context:
                    self.set_user_context(recipient_id, deal.id, ChatInputMode.CHAT)
            else:
                return None

        # 4. Save to History
        self._save_chat_message(deal.id, sender_id, message)
        
        # 5. Track unread count for recipient (if NOT in this chat)
        if not recipient_in_this_chat:
            self.increment_unread(recipient_id, deal.id)
        
        # 6. Check if we should send cross-chat notification
        should_notify = (recipient_in_other_chat or recipient_has_no_context) and self.should_send_cross_chat_notification(recipient_id, deal.id)
        
        return {
            "success": True,
            "recipient_id": recipient_id,
            "recipient_tg_id": recipient_tg_id,
            "should_notify_cross_chat": should_notify,
            "deal_emoji": deal.emoji
        }

    async def notify_deal_start(self, bot: TelegramBotClient, deal: Deal, title: str | None = None) -> None:
        """
        Notifies both parties that the deal has started and sets their chat context.
        """
        # 1. Resolve users
        channel = self.db.query(Channel).get(deal.channel_id)
        if not channel or not channel.owner_id:
            return

        advertiser = self.db.query(User).get(deal.advertiser_id)
        seller = self.db.query(User).get(channel.owner_id)

        if not advertiser or not seller:
            return

        # 2. Validate user ID format matches what Telegram handler uses (tg_{id})
        for u in (advertiser, seller):
            expected = f"tg_{u.telegram_user_id}" if u.telegram_user_id else None
            if expected and u.id != expected:
                logger.error("User ID format mismatch: user.id=%s expected=%s", u.id, expected)

        # 3. Set context for both
        self.set_user_context(advertiser.id, deal.id, ChatInputMode.CHAT)
        self.set_user_context(seller.id, deal.id, ChatInputMode.CHAT)
        self.mark_as_read(advertiser.id, deal.id)
        self.mark_as_read(seller.id, deal.id)

        # 3. Send notifications
        display_title = title or f"Deal #{deal.id}"
        
        # Message to Advertiser
        if advertiser.telegram_user_id:
            await bot.send_message(
                str(advertiser.telegram_user_id),
                f"🎉 <b>Deal started for \"{display_title}\".</b>\n\n"
                f"💬 A chat with the channel owner is open. You can reply to this message to write to them.",
                parse_mode="HTML"
            )

        # Message to Seller
        if seller.telegram_user_id:
            await bot.send_message(
                str(seller.telegram_user_id),
                f"🎉 <b>Deal started for \"{display_title}\".</b>\n\n"
                f"💬 A chat with the advertiser is open. You can reply to this message to write to them.",
                parse_mode="HTML"
            )
