"""
Re-schedule auto-release jobs for all deals currently in 'posted' status.

Usage (from backend/):
    python -m scripts.reschedule_auto_release
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, ".")

from app.db.session import SessionLocal
from app.db.models.deal import Deal, DealStatus
from app.infra.queue.rq import get_scheduler
from app.tasks.auto_release import auto_release_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    db = SessionLocal()
    scheduler = get_scheduler()

    try:
        deals = (
            db.query(Deal)
            .filter(Deal.status == DealStatus.posted.value)
            .all()
        )
        logger.info(f"Found {len(deals)} deal(s) in 'posted' status")

        scheduled = 0
        skipped = 0

        for deal in deals:
            hours = int(deal.post_duration_hours or 0)
            if hours <= 0:
                logger.warning(f"  [{deal.id}] post_duration_hours={deal.post_duration_hours}, skipping")
                skipped += 1
                continue

            published_at_str = deal.published_at
            if not published_at_str:
                logger.warning(f"  [{deal.id}] no published_at, skipping")
                skipped += 1
                continue

            raw = str(published_at_str).strip()
            if raw.endswith("Z"):
                raw = raw.replace("Z", "+00:00")
            try:
                published_at = datetime.fromisoformat(raw)
            except ValueError:
                logger.warning(f"  [{deal.id}] invalid published_at='{published_at_str}', skipping")
                skipped += 1
                continue

            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)

            run_at = published_at + timedelta(hours=hours)
            now = datetime.now(timezone.utc)

            if run_at <= now:
                run_at = now + timedelta(seconds=30)
                logger.info(f"  [{deal.id}] overdue — scheduling in 30 seconds")

            job_id = f"auto_release_{deal.id}_{int(run_at.timestamp())}"

            try:
                scheduler.enqueue_at(run_at, auto_release_task, deal.id, job_id=job_id)
                logger.info(f"  [{deal.id}] scheduled job {job_id} at {run_at.isoformat()}")
                scheduled += 1
            except Exception as e:
                logger.error(f"  [{deal.id}] failed to schedule: {e}", exc_info=True)

        logger.info(f"Done: {scheduled} scheduled, {skipped} skipped")

    finally:
        db.close()


if __name__ == "__main__":
    main()
