import sys
import os

# Add backend directory to sys.path
sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.db.models.deal import Deal

def inspect_deal(deal_id):
    try:
        db = SessionLocal()
        deal = db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            print(f"Deal {deal_id} not found")
            return

        print(f"Deal ID: {deal.id}")
        print(f"Status: {deal.status}")
        print(f"Advertiser Confirmed: {deal.deal_confirmed_by_advertiser} (Type: {type(deal.deal_confirmed_by_advertiser)})")
        print(f"Channel Confirmed: {deal.deal_confirmed_by_channel} (Type: {type(deal.deal_confirmed_by_channel)})")
        print(f"Deal Confirmed At: {deal.deal_confirmed_at}")
        print(f"Scheduled At: {deal.scheduled_at}")
        print(f"Auto Release Hours: {deal.auto_release_hours}")
        print(f"Post Duration Hours: {deal.post_duration_hours}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        inspect_deal(sys.argv[1])
    else:
        print("Usage: python scripts/inspect_deal.py <deal_id>")
