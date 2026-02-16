from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ReviewCreateIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=500)


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    deal_id: str
    reviewer_id: str
    target_user_id: str
    target_channel_id: str | None = None
    target_campaign_id: str | None = None
    rating: int
    comment: str = ""
    reviewer_name: str = ""
    created_at: datetime | None = None
