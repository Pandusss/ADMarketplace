import sys
import os
import logging
from datetime import datetime, timedelta

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.db.session import SessionLocal
from app.db.models.channel import Channel
from app.infra.queue.rq import get_queue, get_scheduler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_status():
    db = SessionLocal()
    try:
        channels = db.query(Channel).all()
        logger.info(f"Found {len(channels)} channels in DB.")
        
        cutoff = datetime.utcnow() - timedelta(hours=12)
        logger.info(f"Cutoff time (12h ago): {cutoff}")

        stale_count = 0
        for ch in channels:
            last_scanned = ch.last_scanned_at
            status = "OK"
            if not last_scanned:
                status = "NEVER SCANNED"
                stale_count += 1
            elif last_scanned < cutoff:
                status = "STALE (>12h)"
                stale_count += 1
            
            logger.info(f"Channel {ch.title} ({ch.id}): Last scanned: {last_scanned} | Status: {status}")

        logger.info("-" * 40)
        logger.info(f"Total stale channels: {stale_count}")

        # Check RQ
        q = get_queue()
        logger.info(f"RQ 'default' queue length: {len(q)}")
        
        scheduler = get_scheduler()
        jobs = list(scheduler.get_jobs())
        logger.info(f"Scheduled jobs count: {len(jobs)}")
        for job in jobs:
            logger.info(f"Job: {job.func_name}, Next Run: {job.started_at if hasattr(job, 'started_at') else 'Custom/Unknown'}")

    except Exception as e:
        logger.exception(f"Error checking status: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_status()
