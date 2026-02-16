"""
Channel verification handler via my_chat_member event.
Checks bot permissions in the channel, manages verification status,
automatically cancels deals when the bot is removed from a channel.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.infra.events import bus as signals
from app.db.models.channel import Channel
from app.db.models.deal import Deal, DealStatus
from app.infra.telegram.bot_client import TelegramBotClient
from app.domain.deals.service import cancel_deal_by_system
from app.infra.queue.rq import get_queue

logger = logging.getLogger(__name__)


from datetime import datetime
from typing import TypedDict, Optional, List, Dict, Any, cast

from app.db.models.channel_verification import ChannelVerification

class ChatMemberUpdate(TypedDict):
    chat: Dict[str, Any]
    from_user: Dict[str, Any]
    new_chat_member: Dict[str, Any]
    old_chat_member: Dict[str, Any]

class VerificationHandler:
    """
    Handles Telegram verification events (my_chat_member updates).
    """

    def __init__(self, bot: TelegramBotClient, db: Session):
        self.db = db
        self.bot = bot
        logger.info(f"VerificationHandler initialized (Bot: {type(bot).__name__})")

    async def handle_my_chat_member(self, update_data: Dict[str, Any]) -> None:
        """
        Process my_chat_member update.
        Logic:
        - If bot is promoted to admin -> Verify channel
        - If bot is kicked/demoted -> Unverify channel + Cancel active deals
        """
        chat = update_data.get("chat", {})
        new_state = update_data.get("new_chat_member", {})
        from_user = update_data.get("from", {})
        
        chat_id = str(chat.get("id"))
        status = new_state.get("status")
        user_id = from_user.get("id")
        
        if not chat_id:
            logger.warning("Received update without chat_id")
            return
            
        logger.debug(f"Handling update for {chat_id}: status={status}, user={user_id}")

        # 1. Promotion (administrator)
        if status == "administrator":
            await self._handle_promotion(
                chat_id=chat_id,
                title=chat.get("title"),
                username=chat.get("username"),
                user_id=user_id
            )
            return

        # 2. Demotion/Kick (kicked, left, member, restricted)
        # "member" means bot is just a user (can't post), so also unverify.
        if status in ("kicked", "left", "member", "restricted"):
            await self.handle_removal(chat_id)
            return
            
        logger.debug(f"Ignored status '{status}' for chat {chat_id}")

    async def _handle_promotion(self, chat_id: str, title: str | None, username: str | None, user_id: int | None) -> None:
        logger.info(f"Processing promotion for {chat_id} by user {user_id}")
        
        # 1. Find existing channel
        channel = self.db.query(Channel).filter(Channel.telegram_channel_id == chat_id).first()
        
        # 2. Find pending verification (if user_id provided)
        verification: Optional[ChannelVerification] = None
        if user_id:
            verification = (
                self.db.query(ChannelVerification)
                .filter(ChannelVerification.telegram_user_id == user_id, ChannelVerification.verified == False)
                .order_by(ChannelVerification.created_at.desc())
                .first()
            )

        # 3. Handle scenarios
        if channel:
            # Scenario A: Channel exists -> Update verified
            logger.info(f"Found existing channel {channel.id}. Updating verification status.")
            channel.is_verified = True
            if title: channel.title = title
            if username: channel.handle = username
            self.db.add(channel)
        
        elif verification:
            # Scenario B: New channel from verification -> Create
            logger.info(f"Creating new channel from verification {verification.token}")
            channel = Channel(
                id=f"ch_{chat_id.replace('-100', '').replace('-', '')}",
                owner_id=verification.user_id,
                telegram_channel_id=chat_id,
                title=title,
                handle=username,
                is_verified=True,
                is_published=False,
                created_at=datetime.utcnow(),
            )
            self.db.add(channel)
        
        else:
            # Scenario C: Unknown channel, no verification -> Ignore
            logger.warning(f"Bot added to unknown channel {chat_id} ({title}) by {user_id}. No pending verification found.")
            return

        # 4. Mark verification as used
        if verification:
            verification.verified = True
            verification.verified_at = datetime.utcnow()
            verification.telegram_channel_id = chat_id
            verification.channel_title = title
            verification.channel_username = username
            self.db.add(verification)
        
        self.db.commit()
        
        # 5. Post-verification actions
        await self._trigger_analytics_update(channel.id, telegram_channel_id=chat_id)
        await self._notify_user_success(channel)

    async def handle_removal(self, chat_id: str) -> None:
        channel = self.db.query(Channel).filter(Channel.telegram_channel_id == chat_id).first()
        
        if not channel or not channel.is_verified:
            return

        logger.warning(f"Bot removed from verified channel {channel.id}. Unverifying...")
        channel.is_verified = False
        self.db.commit()

        # Cancel active deals
        await self._cancel_active_deals(channel)
        
        # Notify user
        await self._notify_user_removal(channel)

    async def _trigger_analytics_update(self, channel_id: str, telegram_channel_id: str | None = None) -> None:
        try:
            invite_link: str | None = None

            # For private channels (no public handle), generate an invite link
            # so the userbot can join via it.
            if telegram_channel_id:
                try:
                    invite_link = await self.bot.create_chat_invite_link(telegram_channel_id)
                    logger.info(f"Generated invite link for {channel_id}: {invite_link}")
                except Exception as e:
                    logger.warning(f"Could not generate invite link for {channel_id}: {e}")

            get_queue().enqueue(
                "app.tasks.analytics_tasks.update_channel_analytics",
                args=(channel_id,),
                kwargs={"invite_link": invite_link},
                job_timeout='10m',
                result_ttl=86400,
                description=f"Initial analytics scan for {channel_id}"
            )
            logger.info(f"Enqueued analytics update for {channel_id}")
        except Exception as e:
            logger.error(f"Failed to enqueue analytics update for {channel_id}: {e}")

    async def _notify_user_success(self, channel: Channel) -> None:
        if not channel.owner_id or not channel.owner_id.startswith("tg_"):
            return
            
        try:
            tg_user_id = channel.owner_id.replace("tg_", "")
            title = channel.title or channel.handle or "your channel"
            await self.bot.send_message(
                tg_user_id,
                f"🎉 <b>Channel Verified!</b>\n\n"
                f"The channel <b>{title}</b> has been successfully added and verified.\n"
                f"You can now configure its pricing and schedule in the app.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to notify user about verification: {e}")

    async def _notify_user_removal(self, channel: Channel) -> None:
        if not channel.owner_id or not channel.owner_id.startswith("tg_"):
            return
            
        try:
            tg_user_id = channel.owner_id.replace("tg_", "")
            title = channel.title or channel.handle or "your channel"
            await self.bot.send_message(
                tg_user_id,
                f"⚠️ <b>Bot Removed</b>\n\n"
                f"The bot was removed from <b>{title}</b>.\n"
                f"The channel is now unverified and hidden.\n"
                f"Any active deals have been cancelled.",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to notify user about removal: {e}")

    async def _cancel_active_deals(self, channel: Channel) -> None:
        """
        Cancels active deals for the channel.
        """
        active_statuses = [
            DealStatus.negotiation.value,
            DealStatus.pending_payment.value,
            DealStatus.creative_draft.value,
            DealStatus.creative_review.value,
            DealStatus.approved.value,
            DealStatus.scheduling.value,
            DealStatus.scheduled.value,
        ]
        
        deals = (
            self.db.query(Deal)
            .filter(
                Deal.channel_id == channel.id,
                Deal.status.in_(active_statuses)
            )
            .all()
        )
        
        if not deals:
            return

        logger.info(f"Cancelling {len(deals)} active deals for unverified channel {channel.id}")

        for deal in deals:
            try:
                await cancel_deal_by_system(self.db, deal.id)
            except Exception as e:
                logger.error(f"Error cancelling deal {deal.id}: {e}")
