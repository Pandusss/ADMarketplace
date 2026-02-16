from __future__ import annotations

"""
Run rq-scheduler for delayed jobs.

Usage (Windows PowerShell):
  cd backend
  python run_rq_scheduler.py
"""

import logging

from app.infra.queue.rq import get_scheduler
from app.tasks.analytics_tasks import dispatch_analytics_updates


def ensure_scheduled_jobs(scheduler) -> None:
    """Ensure critical jobs are scheduled."""
    # Check for existing jobs to avoid dupes/stale entries
    existing_jobs = list(scheduler.get_jobs())
    job_func_name = f"{dispatch_analytics_updates.__module__}.{dispatch_analytics_updates.__name__}"
    
    # Cancel existing to allow updating schedule/args
    for job in existing_jobs:
        if job.func_name == job_func_name:
            scheduler.cancel(job)
            logging.info(f"Cancelled existing job {job.id} to update schedule.")

    # Schedule to run every 15 minutes
    job = scheduler.cron(
        cron_string="*/15 * * * *",  # Every 15 minutes
        func="app.tasks.analytics_tasks.dispatch_analytics_updates",
        queue_name="default",
        repeat=None,
        meta={"description": "Dispatch analytics updates for stale channels"}
    )
    logging.info(f"Scheduled analytics dispatch job: {job.id} (Every 15 mins)")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    scheduler = get_scheduler()
    
    # Register jobs on startup
    ensure_scheduled_jobs(scheduler)
    
    logging.info("RQ Scheduler started.")
    # This blocks and processes scheduled jobs.
    scheduler.run()


if __name__ == "__main__":
    main()

