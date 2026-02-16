from __future__ import annotations

from app.infra.events.signal import Signal
from app.domain.events.types import DealEvent

deal_updated = Signal[DealEvent]("deal_updated")

creative_submitted = Signal[DealEvent]("creative_submitted")

terms_confirmed = Signal[DealEvent]("terms_confirmed")
