import logging
from redis import Redis
from rq import Queue
from rq_scheduler import Scheduler

from app.infra.redis.service import redis_service

logger = logging.getLogger(__name__)

# Primary queue defaults
DEFAULT_QUEUE_NAME = 'default'

def get_redis_conn() -> Redis:
    """Get a raw Redis connection for RQ (non-decoded)."""
    return redis_service.get_connection(decode_responses=False)

def get_queue(name: str = DEFAULT_QUEUE_NAME) -> Queue:
    """Get an RQ queue instance."""
    return Queue(name, connection=get_redis_conn())

def get_scheduler() -> Scheduler:
    """Get an RQ scheduler instance."""
    return Scheduler(connection=get_redis_conn())

def enqueue_job(func, *args, queue_name: str = DEFAULT_QUEUE_NAME, **kwargs):
    """Convenience helper to enqueue a job."""
    q = get_queue(queue_name)
    return q.enqueue(func, *args, **kwargs)
