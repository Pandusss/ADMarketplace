from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_

from app.db.session import SessionLocal
from app.db.models.deal import Deal, DealStatus
from app.domain.deals.service import transition, TransitionConflict, cancel_deal_by_system
from app.infra.ton.escrow import TonEscrowService
from app.domain.chat.service import ChatService

logger = logging.getLogger(__name__)

# Timeout configuration
# Determine how long a deal can stay in a specific state before being cancelled/refunded.
TIMEOUTS = {
    DealStatus.negotiation: timedelta(hours=24),
    DealStatus.pending_payment: timedelta(hours=24),
    DealStatus.creative_draft: timedelta(hours=48),
    DealStatus.creative_review: timedelta(hours=48),
    # 'approved' means the creative is approved but no slot is requested yet.
    DealStatus.approved: timedelta(hours=24),
    DealStatus.scheduling: timedelta(hours=24),
    # Note: 'scheduled' deals are usually waiting for a future date, so simple inactivity 
    # check on updated_at is risky. We skip 'scheduled' for this generic timeout.
}

def cancel_stale_deals() -> dict:
    """
    RQ job: Automatically cancel deals that have been inactive for too long.
    
    Iterates through states defined in TIMEOUTS and finds deals where 
    updated_at is older than the allowed threshold.
    """
    logger.info("Starting cancel_stale_deals job")
    db = SessionLocal()
    stats = {"scanned": 0, "cancelled": 0, "refunded": 0, "errors": 0}
    
    try:
        now_utc = datetime.now(timezone.utc)
        
        # We process each status separately to apply the correct timeout.
        for status_enum, timeout_delta in TIMEOUTS.items():
            cutoff_time = now_utc - timeout_delta
            
            # Find deals in this status that haven't been updated since cutoff_time
            # Note: stored datetime in DB might be naive (UTC), so we might need comparison adjustment.
            # Assuming app convention is UTC.
            
            stale_deals = db.query(Deal).filter(
                Deal.status == status_enum.value,
                Deal.updated_at < cutoff_time
            ).all() # Fetch all to iterate and transition individually
            
            for deal in stale_deals:
                stats["scanned"] += 1
                deal_id = deal.id
                current_status = deal.status
                
                logger.info(f"Processing stale deal {deal_id} (Status: {current_status}, Last Update: {deal.updated_at})")
                
                # Determine intended action. If the deal has funds (see state_machine logic),
                # 'cancel' action will fail or we rely on state machine to convert it to refund.
                # However, state_machine.transition handles 'cancel' by checking if it allows 
                # refund. Let's look at state_machine.py:
                # - 'cancel' action:
                #    - negotiation/pending_payment -> cancelled
                #    - creative_draft/review/approved/scheduling/scheduled -> refunded
                # So 'cancel' action is polymorphic in our SM.
                
                try:
                    # Use the robust system cancellation method which handles refunds, signals, etc.
# Already imported at top
                    
                    # We need to await this, but cancel_stale_deals is sync (RQ job).
                    # Solution: use asyncio.run or similar.
                    # Since RQ worker handles async context? No, standard python-rq is sync.
                    # We need to wrap it.
                    import asyncio
                    res_deal = asyncio.run(cancel_deal_by_system(db, deal_id))
                    
                    new_status = res_deal.status
                    if "refunded" in new_status:
                        stats["refunded"] += 1
                    else:
                        stats["cancelled"] += 1
                        
                    logger.info(f"Successfully transitioned deal {deal_id} from {current_status} to {new_status}")
                    
                except TransitionConflict as e:
                    logger.warning(f"Could not cancel stale deal {deal_id}: {e}")
                    stats["errors"] += 1
                except Exception as e:
                    logger.exception(f"Unexpected error cancelling deal {deal_id}: {e}")
                    stats["errors"] += 1
                    
        logger.info(f"cancel_stale_deals completed. Stats: {stats}")
        return stats
        
    finally:
        db.close()
