from __future__ import annotations
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.infra.queue.rq import get_scheduler

def inspect():
    scheduler = get_scheduler()
    jobs = list(scheduler.get_jobs())
    print(f"Total jobs in scheduler: {len(jobs)}")
    for j in jobs:
        print(f"ID: {j.id} | Func: {j.func_name} | Cron: {getattr(j, 'cron_string', 'N/A')} | Next run: {j.started_at}")

if __name__ == "__main__":
    inspect()
