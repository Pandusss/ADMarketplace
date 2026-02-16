from __future__ import annotations

"""
Schedule the deal cleanup task to run periodically.

Usage:
  cd backend
  python scripts/schedule_cleanup.py
"""

import logging
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.infra.queue.rq import get_scheduler
from app.tasks.cleanup_tasks import cancel_stale_deals

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def schedule_cleanup_job() -> None:
    scheduler = get_scheduler()
    
    # Cancel existing job if needed (to avoid duplicates if re-running script)
    # Note: rq-scheduler doesn't have an easy "get_job_by_func" without iterating.
    # For now, we'll just schedule it. If multiple exist, they'll all run (harmless but inefficient).
    # Ideally, one would check `scheduler.get_jobs()` and comparisons.
    
    # Let's inspect existing jobs to avoid excessive duplication
    existing_jobs = list(scheduler.get_jobs())
    job_func_name = f"{cancel_stale_deals.__module__}.{cancel_stale_deals.__name__}"
    
    for job in existing_jobs:
        if job.func_name == job_func_name:
            logger.info(f"Cleanup job {job.id} already exists. Skipping re-schedule.")
            return

    # Schedule to run every 1 hour
    job = scheduler.cron(
        cron_string="0 * * * *",  # Every hour at minute 0
        func="app.tasks.cleanup_tasks.cancel_stale_deals",
        queue_name="default",
        repeat=None,              # Infinite
        meta={"description": "Cancel stale deals"}
    )
    
    logger.info(f"Scheduled cleanup job: {job.id} (Every hour)")
    logger.info(f"Next run at: {job.started_at if hasattr(job, 'started_at') else 'Scheduled'}")

if __name__ == "__main__":
    schedule_cleanup_job()
