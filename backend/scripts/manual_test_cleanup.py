from __future__ import annotations

import sys
import os
import secrets
from datetime import datetime, timedelta

# Add backend to path so we can import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from app.models.deal import Deal, DealStatus
from app.tasks.cleanup_tasks import cancel_stale_deals, TIMEOUTS

def setup_test_data(db):
    print("Setting up test data...")
    
    # Create deals in various states
    deals = []
    
    # 1. Negotiation - Stale (Should be cancelled)
    d1 = Deal(
        id=f"test_neg_stale_{secrets.token_hex(4)}",
        channel_id="test_channel",
        advertiser_id="test_adv",
        status=DealStatus.negotiation.value,
        updated_at=datetime.utcnow() - TIMEOUTS[DealStatus.negotiation] - timedelta(hours=1)
    )
    
    # 2. Negotiation - Fresh (Should NOT be cancelled)
    d2 = Deal(
        id=f"test_neg_fresh_{secrets.token_hex(4)}",
        channel_id="test_channel",
        advertiser_id="test_adv",
        status=DealStatus.negotiation.value,
        updated_at=datetime.utcnow() - TIMEOUTS[DealStatus.negotiation] + timedelta(hours=1)
    )
    
    # 3. Creative Draft - Stale (Should be REFUNDED)
    d3 = Deal(
        id=f"test_draft_stale_{secrets.token_hex(4)}",
        channel_id="test_channel",
        advertiser_id="test_adv",
        status=DealStatus.creative_draft.value,
        updated_at=datetime.utcnow() - TIMEOUTS[DealStatus.creative_draft] - timedelta(hours=1)
    )
         
    db.add_all([d1, d2, d3])
    db.commit()
    return [d1.id, d2.id, d3.id]

def verify_results(db, deal_ids):
    print("\nVerifying results...")
    d1 = db.query(Deal).filter(Deal.id == deal_ids[0]).one()
    d2 = db.query(Deal).filter(Deal.id == deal_ids[1]).one()
    d3 = db.query(Deal).filter(Deal.id == deal_ids[2]).one()
    
    print(f"Deal 1 (Negotiation Stale): {d1.status} (Expected: cancelled)")
    print(f"Deal 2 (Negotiation Fresh): {d2.status} (Expected: negotiation)")
    print(f"Deal 3 (Draft Stale): {d3.status} (Expected: refunded)")

    if d1.status == DealStatus.cancelled.value:
         print("PASS: Deal 1 cancelled correctly")
    else:
         print("FAIL: Deal 1 not cancelled")

    if d2.status == DealStatus.negotiation.value:
         print("PASS: Deal 2 ignored correctly")
    else:
         print("FAIL: Deal 2 was modified")
         
    if d3.status == DealStatus.refunded.value:
         print("PASS: Deal 3 refunded correctly")
    else:
         print(f"FAIL: Deal 3 not refunded (status={d3.status})")

def main():
    db = SessionLocal()
    try:
        deal_ids = setup_test_data(db)
        print(f"Created deals: {deal_ids}")
        
        print("\nRunning cleanup task...")
        stats = cancel_stale_deals()
        print(f"Task stats: {stats}")
        
        verify_results(db, deal_ids)
        
        # Cleanup
        print("\nCleaning up test data...")
        db.query(Deal).filter(Deal.id.in_(deal_ids)).delete(synchronize_session=False)
        db.commit()
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
