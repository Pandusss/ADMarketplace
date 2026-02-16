"""
Centralized Redis service for the entire application.

This module provides a single source of truth for all Redis connections:
- Chat system (user contexts, unread counts)
- Background jobs (RQ)
- WebSocket pub/sub (deal updates)

All Redis usage should go through this service for consistency.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import redis
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Constants
REDIS_CONNECT_TIMEOUT_SEC = 2
REDIS_SOCKET_TIMEOUT_SEC = 2
CONTEXT_TTL_HOURS = 24
UNREAD_TTL_DAYS = 30
ACTIVE_DEALS_CACHE_TTL_MINUTES = 10
SCAN_COUNT = 100


class RedisService:
    """
    Centralized Redis service with automatic fallback.
    
    Provides:
    1. Sync Redis connection (for chat, RQ)
    2. Chat-specific methods (user context, unread counts)
    3. Graceful degradation if Redis unavailable
    
    Key patterns:
    - ctx:{user_id} - User chat context
    - unread:{user_id}:{deal_id} - Unread count data
    - active_deals:{user_id} - Cached active deals list
    - deal_updates - Pub/sub channel for WebSocket
    """
    
    def __init__(self):
        """Initialize Redis connection."""
        try:
            self.redis = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=REDIS_CONNECT_TIMEOUT_SEC,
                socket_timeout=REDIS_SOCKET_TIMEOUT_SEC
            )
            # Test connection
            self.redis.ping()
            self.available = True
            logger.info("Redis connected successfully")
        except RedisError as e:
            logger.warning(f"Redis connection failed: {e}")
            logger.info("Will use database fallback for chat features")
            self.redis = None
            self.available = False
    
    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self.available and self.redis is not None
    
    def get_connection(self, decode_responses: bool = True) -> Redis:
        """
        Get raw Redis connection for advanced usage (RQ, pub/sub).
        
        Args:
            decode_responses: Whether to decode responses to strings.
                             Set to False for RQ (binary payloads).
        
        Returns:
            Redis connection instance.
        """
        return redis.from_url(
            settings.redis_url,
            decode_responses=decode_responses
        )
    
    # ========== Helper Methods ==========
    
    @staticmethod
    def _make_context_key(user_id: str) -> str:
        """Generate Redis key for user context."""
        return f"ctx:{user_id}"
    
    @staticmethod
    def _make_unread_key(user_id: str, deal_id: str) -> str:
        """Generate Redis key for unread count."""
        return f"unread:{user_id}:{deal_id}"
    
    @staticmethod
    def _make_active_deals_key(user_id: str) -> str:
        """Generate Redis key for active deals cache."""
        return f"active_deals:{user_id}"
    
    def _log_error(self, operation: str, error: Exception, **context) -> None:
        """Log Redis operation error with context."""
        logger.error(f"Redis {operation} failed: {error}", extra=context, exc_info=False)
    
    # ========== User Context Methods ==========
    
    def get_user_context(self, user_id: str) -> Optional[dict]:
        """
        Get user chat context from Redis.
        Returns None if not found or Redis unavailable.
        """
        if not self.is_available():
            return None
        
        try:
            data = self.redis.get(self._make_context_key(user_id))
            if data:
                return json.loads(data)
        except (RedisError, json.JSONDecodeError) as e:
            self._log_error("get_user_context", e, user_id=user_id)
        
        return None
    
    def set_user_context(self, user_id: str, deal_id: str, input_mode: str) -> bool:
        """
        Set user chat context in Redis.
        TTL: 24 hours
        Returns True if successful.
        """
        if not self.is_available():
            return False
        
        try:
            data = {
                "deal_id": deal_id,
                "input_mode": input_mode,
                "updated_at": datetime.utcnow().isoformat()
            }
            self.redis.setex(
                self._make_context_key(user_id),
                timedelta(hours=CONTEXT_TTL_HOURS),
                json.dumps(data)
            )
            return True
        except RedisError as e:
            self._log_error("set_user_context", e, user_id=user_id, deal_id=deal_id)
            return False
    
    def clear_user_context(self, user_id: str) -> bool:
        """
        Clear user chat context from Redis.
        Returns True if successful.
        """
        if not self.is_available():
            return False
        
        try:
            self.redis.delete(self._make_context_key(user_id))
            return True
        except RedisError as e:
            self._log_error("clear_user_context", e, user_id=user_id)
            return False
    
    # ========== Unread Count Methods ==========
    
    def get_unread_count(self, user_id: str, deal_id: str) -> Optional[dict]:
        """
        Get unread count data for a user-deal pair.
        Returns dict with: count, cross_chat_notified, last_read_at
        """
        if not self.is_available():
            return None
        
        try:
            data = self.redis.hgetall(self._make_unread_key(user_id, deal_id))
            if data:
                return {
                    "count": int(data.get("count", 0)),
                    "cross_chat_notified": int(data.get("notified", 0)),
                    "last_read_at": data.get("last_read_at")
                }
        except (RedisError, ValueError) as e:
            self._log_error("get_unread_count", e, user_id=user_id, deal_id=deal_id)
        
        return None
    
    def get_all_unread_counts(self, user_id: str) -> dict[str, int]:
        """
        Get all unread counts for a user.
        Returns dict: {deal_id: count}
        """
        if not self.is_available():
            return {}
        
        try:
            counts = {}
            pattern = f"unread:{user_id}:*"
            for key in self.redis.scan_iter(pattern, count=SCAN_COUNT):
                data = self.redis.hget(key, "count")
                if data:
                    deal_id = key.split(":")[-1]
                    counts[deal_id] = int(data)
            return counts
        except (RedisError, ValueError) as e:
            self._log_error("get_all_unread_counts", e, user_id=user_id)
            return {}
    
    def increment_unread(self, user_id: str, deal_id: str) -> bool:
        """
        Increment unread count for a user-deal pair.
        TTL: 30 days
        """
        if not self.is_available():
            return False
        
        try:
            key = self._make_unread_key(user_id, deal_id)
            pipe = self.redis.pipeline()
            pipe.hincrby(key, "count", 1)
            pipe.hsetnx(key, "notified", 0)
            pipe.hsetnx(key, "last_read_at", datetime.utcnow().isoformat())
            pipe.expire(key, timedelta(days=UNREAD_TTL_DAYS))
            pipe.execute()
            return True
        except RedisError as e:
            self._log_error("increment_unread", e, user_id=user_id, deal_id=deal_id)
            return False
    
    def mark_as_read(self, user_id: str, deal_id: str) -> bool:
        """
        Mark all messages as read (reset count to 0).
        """
        if not self.is_available():
            return False
        
        try:
            key = self._make_unread_key(user_id, deal_id)
            pipe = self.redis.pipeline()
            pipe.hset(key, "count", 0)
            pipe.hset(key, "notified", 0)
            pipe.hset(key, "last_read_at", datetime.utcnow().isoformat())
            pipe.expire(key, timedelta(days=UNREAD_TTL_DAYS))
            pipe.execute()
            return True
        except RedisError as e:
            self._log_error("mark_as_read", e, user_id=user_id, deal_id=deal_id)
            return False
    
    def update_last_read_timestamp(self, user_id: str, deal_id: str) -> bool:
        """
        Update last_read_at timestamp (for real-time message delivery).
        """
        if not self.is_available():
            return False
        
        try:
            key = self._make_unread_key(user_id, deal_id)
            pipe = self.redis.pipeline()
            pipe.hsetnx(key, "count", 0)
            pipe.hsetnx(key, "notified", 0)
            pipe.hset(key, "last_read_at", datetime.utcnow().isoformat())
            pipe.expire(key, timedelta(days=UNREAD_TTL_DAYS))
            pipe.execute()
            return True
        except RedisError as e:
            self._log_error("update_last_read_timestamp", e, user_id=user_id, deal_id=deal_id)
            return False
    
    def mark_cross_chat_notified(self, user_id: str, deal_id: str) -> bool:
        """
        Mark that cross-chat notification has been sent.
        """
        if not self.is_available():
            return False
        
        try:
            self.redis.hset(self._make_unread_key(user_id, deal_id), "notified", 1)
            return True
        except RedisError as e:
            self._log_error("mark_cross_chat_notified", e, user_id=user_id, deal_id=deal_id)
            return False
    
    # ========== Active Deals Cache ==========
    
    def get_active_deals_cache(self, user_id: str) -> Optional[list[str]]:
        """
        Get cached active deals list.
        Returns list of deal IDs or None if not cached.
        """
        if not self.is_available():
            return None
        
        try:
            data = self.redis.get(self._make_active_deals_key(user_id))
            if data:
                return json.loads(data)
        except (RedisError, json.JSONDecodeError) as e:
            self._log_error("get_active_deals_cache", e, user_id=user_id)
        
        return None
    
    def set_active_deals_cache(self, user_id: str, deal_ids: list[str]) -> bool:
        """
        Cache active deals list.
        TTL: 10 minutes
        """
        if not self.is_available():
            return False
        
        try:
            self.redis.setex(
                self._make_active_deals_key(user_id),
                timedelta(minutes=ACTIVE_DEALS_CACHE_TTL_MINUTES),
                json.dumps(deal_ids)
            )
            return True
        except RedisError as e:
            self._log_error("set_active_deals_cache", e, user_id=user_id)
            return False
    
    def invalidate_active_deals_cache(self, user_id: str) -> bool:
        """
        Invalidate active deals cache (when deals change).
        """
        if not self.is_available():
            return False
        
        try:
            self.redis.delete(self._make_active_deals_key(user_id))
            return True
        except RedisError as e:
            self._log_error("invalidate_active_deals_cache", e, user_id=user_id)
            return False


# Global Redis instance
redis_service = RedisService()
