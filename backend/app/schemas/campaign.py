import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CampaignCreateIn(BaseModel):
    title: str = Field(min_length=1)
    brief: str = Field(min_length=1)
    category: Optional[str] = None
    language: Optional[str] = None
    budget_ton: Optional[float] = None
    desired_views_24h: Optional[int] = Field(default=None, ge=1)
    template_id: Optional[str] = None
    creative_mode: str = "template"
    creative_instructions: Optional[str] = None
    post_duration_hours: int = 24


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    title: str
    brief: str
    category: str
    language: str
    budget_ton: float
    desired_views_24h: Optional[int] = None
    template_id: str
    creative_mode: str
    creative_instructions: Optional[str] = None
    post_duration_hours: int = 24
    status: str
    created_at: Optional[datetime.datetime] = None
    owner_rating_avg: float = 0.0
    owner_rating_count: int = 0
    rating_avg: float = 0.0
    rating_count: int = 0

CampaignOut.model_rebuild()
