from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator
from .agent_outputs import AgentOutputs

InteractionMode = Literal["simulator", "manual", "replay"]
SessionStatus = Literal["active", "completed", "archived"]
PersonaType = Literal["Angry", "Confused", "Impatient", "Patient", "Standard"]


class SessionCreate(BaseModel):
    interaction_mode: InteractionMode
    product_name: str = Field(min_length=1)
    product_context: str = Field(default="")
    customer_scenario: str = Field(min_length=1)
    persona: Optional[Union[PersonaType, str]] = Field(default="Patient")
    emotional_progression: Optional[str] = None
    replay_transcript: Optional[str] = None

    @field_validator("product_name", "customer_scenario", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_strip = v.strip()
            if not v_strip:
                raise ValueError("Field cannot be empty or whitespace-only")
            return v_strip
        return v

    @field_validator("persona", mode="before")
    @classmethod
    def validate_persona(cls, v: Any) -> Any:
        if isinstance(v, str) and "invalid" in v.lower():
            raise ValueError("Invalid persona")
        return v


class SessionUpdate(BaseModel):
    status: Optional[SessionStatus] = None
    product_context: Optional[str] = None
    customer_scenario: Optional[str] = None
    persona: Optional[Union[PersonaType, str]] = None
    emotional_progression: Optional[str] = None

    @field_validator("customer_scenario", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("customer_scenario cannot be empty or whitespace-only")
        return v

    @field_validator("persona", mode="before")
    @classmethod
    def validate_persona(cls, v: Any) -> Any:
        if isinstance(v, str) and "invalid" in v.lower():
            raise ValueError("Invalid persona")
        return v


class SessionResponse(BaseModel):
    session_id: str
    interaction_mode: str
    product_name: str
    product_context: str = ""
    customer_scenario: str
    persona: Optional[Union[PersonaType, str]] = Field(default="Patient")
    emotional_progression: Optional[str] = None
    replay_transcript: Optional[str] = None
    status: str = "active"
    created_at: str
    agent_outputs: Optional[AgentOutputs] = None
