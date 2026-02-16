from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PaymentStatus = Literal["unpaid", "paid", "refunded"]


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    deal_id: str
    amount_usdt: int = Field(ge=0)
    status: PaymentStatus
    paid_at: str | None = None

