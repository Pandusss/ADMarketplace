from __future__ import annotations

from typing import Any


class DealEvent:
    def __init__(self, deal_id: str, actor_id: str | None = None, event_type: str | None = None, metadata: dict[str, Any] | None = None):
        self.deal_id = deal_id
        self.actor_id = actor_id
        self.event_type = event_type
        self.metadata = metadata or {}
