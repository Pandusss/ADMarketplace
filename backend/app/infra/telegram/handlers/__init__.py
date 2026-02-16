"""
Telegram Bot Update Handlers.
Roots all incoming Telegram updates (commands, callbacks, messages) 
to their respective specialized processing modules.
"""
from __future__ import annotations
import logging
from sqlalchemy.orm import Session
from app.infra.telegram.bot_client import TelegramBotClient
from .command_handler import CommandHandler
from .callback_handler import CallbackHandler
from .chat_handler import ChatHandler
from .verification_handler import VerificationHandler

logger = logging.getLogger(__name__)

async def process_update(update: dict, db: Session, bot: TelegramBotClient):
    """
    Central dispatcher for all Telegram updates.
    """
    # 1. Callback Queries
    if "callback_query" in update:
        handler = CallbackHandler(bot, db)
        await handler.handle_callback(update["callback_query"])
        return

    # 2. My Chat Member (Verification)
    if "my_chat_member" in update:
        handler = VerificationHandler(bot, db)
        await handler.handle_my_chat_member(update["my_chat_member"])
        return

    # 3. Messages
    if "message" in update:
        msg = update["message"]
        text = msg.get("text", "")
        chat_id = msg.get("chat", {}).get("id")
        user_id = msg.get("from", {}).get("id")

        if not chat_id or not user_id:
            return

        # 4. Left Chat Member (Bot removed)
        left_member = msg.get("left_chat_member")
        if left_member:
            # We don't have easy access to bot's ID here without an extra call or config.
            # However, if the bot sees this message, it usually means *someone* left.
            # If the bot itself left, it might not receive the message in some cases,
            # BUT if it was removed by admin, it often gets a "left_chat_member" service message locally logic.
            # We should check if left_member["id"] is the bot. 
            # Ideally we'd know bot_id. For now, let's assume if we see this event in a channel/group context
            # where we track verification, we should check it.
            # Actually, `my_chat_member` is preferred for bot logic.
            # But the user says `my_chat_member` didn't fire or wasn't enough.
            
            # Let's try to fetch bot info if not cached, or just try to unverify if the ID matches.
            # Optimization: We'll just call the handler. The handler checks DB.
            # If we pass a random user ID, it won't match "bot removed" necessarily?
            # Wait, `handle_removal` takes `chat_id`. It verifies if the Channel exists and is verified.
            # If a *user* leaves, we shouldn't unverify the channel.
            # We must ensure `left_member` IS the bot.
            
            # We can get bot ID from `bot.id` if available, or `bot.get_me()`.
            # `TelegramBotClient` in this codebase might not have `id` property readily available without an API call.
            # Let's check `bot.token`.
            try:
                # Token format: 123456:ABC-DEF...
                bot_id = int(bot.token.split(":")[0])
                if left_member.get("id") == bot_id:
                     handler = VerificationHandler(bot, db)
                     await handler.handle_removal(str(chat_id))
                     return
            except Exception:
                pass

        if text.startswith("/"):
            handler = CommandHandler(bot, db)
            if text.startswith("/start"):
                await handler.handle_start(str(chat_id), user_id, text)
            elif text.startswith("/chats"):
                await handler.handle_chats(str(chat_id), user_id)
            return

        # Regular messages (Chat)
        handler = ChatHandler(bot, db)
        await handler.handle_message(msg)
        return

    logger.debug(f"Unhandled update type: {list(update.keys())}")