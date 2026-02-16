"""
RQ Worker Entry Point.
Starts a Redis Queue worker instance to process background tasks 
such as analytics updates, cleanup jobs, and event-driven signals.
"""

import logging

import os

# RQ Worker doesn't support os.fork() on Windows.
# We use SimpleWorker for local Windows dev and standard Worker for Linux prod.
if os.name == 'nt':
    from rq import SimpleWorker as Worker
else:
    from rq import Worker

from app.infra.queue.rq import get_queue


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    
    # Register signal handlers so that signals emitted by jobs 
    # (e.g. deal_updated) trigger Redis updates via notifications.py
    # This is critical for WebSocket updates to frontend.
    from app.domain.events.handlers import register_signal_handlers
    try:
        register_signal_handlers()
    except Exception as e:
        logging.error(f"Failed to register signal handlers: {e}")

    q = get_queue()
    worker = Worker([q], connection=q.connection)
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
