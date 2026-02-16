from __future__ import annotations

"""
Schedule the channel analytics update task to run periodically (Hourly).

Usage:
  cd backend
  python scripts/schedule_analytics.py
"""

import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.infra.queue.rq import get_scheduler
from app.tasks.analytics_tasks import dispatch_analytics_updates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def schedule_analytics_job() -> None:
    scheduler = get_scheduler()
    
    # Check for existing jobs to avoid dupes
    existing_jobs = list(scheduler.get_jobs())
    job_func_name = f"{dispatch_analytics_updates.__module__}.{dispatch_analytics_updates.__name__}"
    
    for job in existing_jobs:
        if job.func_name == job_func_name:
            scheduler.cancel(job)
            logger.info(f"Cancelled existing job {job.id} to update schedule.")

    # Schedule to run every 15 minutes
    job = scheduler.cron(
        cron_string="*/15 * * * *",  # Every 15 minutes
        func="app.tasks.analytics_tasks.dispatch_analytics_updates",
        queue_name="default",
        repeat=None,              # Infinite
        meta={"description": "Dispatch analytics updates for stale channels"}
    )
    
    logger.info(f"Scheduled analytics dispatch job: {job.id} (Every hour)")
    logger.info(f"Next run at: {job.started_at if hasattr(job, 'started_at') else 'Scheduled'}")

if __name__ == "__main__":
    schedule_analytics_job()
