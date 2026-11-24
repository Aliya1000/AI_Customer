from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator
from .agent_outputs import AgentOutputs

MessageSender = Literal["employee", "customer", "system"]


class MessageCreate(BaseModel):
    sender: Literal["employee", "customer"] = "employee"
    message_text: str = Field(min_length=1)

    @field_validator("message_text", mode="after")
    @classmethod
    def validate_not_whitespace(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("message_text cannot be empty or whitespace-only")
        return v


class MessageResponse(BaseModel):
    message_id: str
    session_id: str
    sender: str
    message_text: str
    timestamp: str


class SendMessageResponse(BaseModel):
    saved_message: MessageResponse
    simulated_customer_reply: Optional[MessageResponse] = None
    agent_outputs: AgentOutputs
