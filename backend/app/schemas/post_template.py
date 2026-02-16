from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, computed_field
import json


class PostTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str

    waiting_for_content: bool = False

    creative_type: str | None = None
    creative_message_ids: list[int] | None = None

    # Inline preview snapshot (COMPROMISE)
    preview_text: str = ""
    # Removed flags from regular fields to use @computed_field
    preview_count: int = 0

    @computed_field
    @property
    def preview_has_media(self) -> bool:
        return bool((self.preview_file_id or "").strip() or (self.preview_file_ids or "").strip())

    @computed_field
    @property
    def has_content(self) -> bool:
        return bool(self.creative_message_ids)

    # These fields are required for the computed_field but can be hidden if needed.
    preview_file_id: str = ""
    preview_file_ids: str = ""

    @field_validator("creative_message_ids", mode="before")
    @classmethod
    def decode_json_list(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return None
        return v




class PostTemplateCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=60)


class UseTemplateIn(BaseModel):
    template_id: str

