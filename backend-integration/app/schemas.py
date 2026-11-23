
from typing import Any, Optional
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, ConfigDict


class SessionCreate(BaseModel):

    interaction_mode: str

    product_name: str = Field(..., min_length=1)
    product_context: str = Field(..., min_length=1)

    customer_scenario: str = Field(..., min_length=1)
    persona: str = Field(..., min_length=1)

    emotional_progression: Optional[Any] = None
    replay_transcript: Optional[Any] = None

    @field_validator("interaction_mode")
    @classmethod
    def validate_interaction_mode(cls, value):
        value = value.strip().lower()

        allowed_modes = ["simulator", "manual", "replay"]

        if value not in allowed_modes:
            raise ValueError(
                "interaction_mode must be simulator, manual, or replay"
            )

        return value

    @field_validator(
        "product_name",
        "product_context",
        "customer_scenario",
        "persona"
    )
    @classmethod
    def validate_required_text(cls, value):
        if not value.strip():
            raise ValueError("This field cannot be empty")

        return value.strip()


class SessionResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    session_id: str
    interaction_mode: str

    product_name: str
    product_context: str

    customer_scenario: str
    persona: str

    emotional_progression: Optional[Any] = None
    replay_transcript: Optional[Any] = None

    status: str

    created_at: datetime
    updated_at: Optional[datetime] = None
