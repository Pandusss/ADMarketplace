from __future__ import annotations
import datetime
from app.db.session import SessionLocal
from app.db.models.channel import Channel

def dump():
    db = SessionLocal()
    now = datetime.datetime.utcnow()
    channels = db.query(Channel).all()
    
    with open('channel_dump.txt', 'w', encoding='utf-8') as f:
        f.write(f"Current UTC: {now}\n")
        f.write(f"Total channels: {len(channels)}\n\n")
        f.write("ID | Handle | LastScanned | Verified | Subscribers | AvgViews | Stale(24h)\n")
        f.write("-" * 80 + "\n")
        for c in channels:
            stale = c.last_scanned_at is None or (now - c.last_scanned_at).total_seconds() > 86400
            f.write(f"{c.id} | {c.handle} | {c.last_scanned_at} | {c.verified_stats} | {c.subscribers_count} | {c.avg_views} | {stale}\n")
    db.close()

if __name__ == "__main__":
    dump()
