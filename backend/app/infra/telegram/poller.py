from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models.telegram_update_state import TelegramUpdateState
from app.infra.telegram.bot_client import TelegramApiError, TelegramBotClient

logger = logging.getLogger(__name__)

# Polling configuration constants
POLL_INTERVAL_SEC = 0.5
API_ERROR_RETRY_SEC = 2.0
UNEXPECTED_ERROR_RETRY_SEC = 5.0
STATE_ID = 1  # Single global state for update tracking


async def run_polling_loop(process_update) -> None:
    """
    Poll Telegram getUpdates and feed updates into `process_update(update, db_session)`.
    Webhook-free mode.
    
    Optimized to minimize DB transactions.
    """

    if not settings.telegram_bot_token:
        logger.warning("Telegram bot token not configured, polling disabled")
        return

    bot = TelegramBotClient(settings.telegram_bot_token)
    current_offset: Optional[int] = None

    # Initial DB read to get offset
    try:
        db = SessionLocal()
        try:
            state = db.query(TelegramUpdateState).filter(TelegramUpdateState.id == STATE_ID).one_or_none()
            if not state:
                logger.info("Creating initial Telegram update state")
                state = TelegramUpdateState(id=STATE_ID, last_update_id=0, updated_at=datetime.utcnow())
                db.add(state)
                db.commit()
                db.refresh(state)
            
            if state.last_update_id:
                current_offset = int(state.last_update_id) + 1
                logger.info(f"Resuming polling from update_id {state.last_update_id} (offset {current_offset})")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to initialize polling state: {e}", exc_info=True)
        return

    logger.info("Initializing persistent bot client...")
    await bot.start()

    try:
        logger.info("Deleting webhook to enable polling mode...")
        try:
            await bot.delete_webhook(drop_pending_updates=False) # Keep pending updates, we want them
        except Exception as e:
             logger.warning(f"Webhook deletion warning (ignorable if already deleted): {e}")

        logger.info("Entering polling loop")
        
        while True:
            try:
                # 1. Fetch updates
                try:
                    updates = await bot.get_updates(offset=current_offset, timeout=settings.telegram_poll_timeout_sec)
                except asyncio.CancelledError:
                    logger.info("Polling loop cancelled")
                    return
                except TelegramApiError as e:
                    # 409 Conflict can happen if another instance is running
                    if "Conflict" in str(e):
                        logger.critical("Telegram Conflict Error: Another bot instance is running? Retrying in 5s...")
                        await asyncio.sleep(5)
                    else:
                        logger.error(f"Telegram API warning: {e.message}")
                        await asyncio.sleep(API_ERROR_RETRY_SEC)
                    continue
                except Exception as e:
                    logger.error(f"Network/Unexpected error during getUpdates: {e}")
                    await asyncio.sleep(UNEXPECTED_ERROR_RETRY_SEC)
                    continue

                # 2. Process updates
                if updates:
                    logger.info(f"Received {len(updates)} update(s)")
                    
                    # Sort by update_id to be safe
                    updates.sort(key=lambda x: x.get("update_id", 0))
                    
                    max_processed_id = None
                    
                    db = SessionLocal()
                    try:
                        for upd in updates:
                            upd_id = upd.get("update_id")
                            if not upd_id: continue

                            try:
                                # Process logic
                                await process_update(upd, db, bot)
                            except Exception as e:
                                logger.error(f"Error processing update {upd_id}: {e}", exc_info=True)
                            
                            max_processed_id = upd_id

                        # 3. Update offset in DB (Checkpoint)
                        if max_processed_id is not None:
                            # Update local memory offset
                            current_offset = max_processed_id + 1
                            
                            # Update DB state
                            state = db.query(TelegramUpdateState).filter(TelegramUpdateState.id == STATE_ID).one_or_none()
                            if state:
                                state.last_update_id = max_processed_id
                                state.updated_at = datetime.utcnow()
                                db.commit()
                                
                    finally:
                        db.close()
                
                # 4. Sleep briefly
                await asyncio.sleep(POLL_INTERVAL_SEC)

            except asyncio.CancelledError:
                 logger.info("Polling loop stopping...")
                 return
            except Exception as e:
                logger.critical(f"Unhandled error in polling loop: {e}", exc_info=True)
                await asyncio.sleep(UNEXPECTED_ERROR_RETRY_SEC)
    finally:
        logger.info("Closing persistent bot client...")
        await bot.stop()
