from typing import List, Optional
from pydantic import BaseModel, Field


class CoachingReportCreate(BaseModel):
    report_id: Optional[str] = None
    session_id: str
    conversation_summary: str
    customer_sentiment: str = "Neutral"
    evaluation_score: int = Field(ge=0, le=100)
    employee_evaluation: str = ""
    strengths: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    recommended_replies: List[str] = Field(default_factory=list)


class CoachingReportResponse(BaseModel):
    report_id: str
    session_id: str
    conversation_summary: str
    customer_sentiment: str
    evaluation_score: int = Field(ge=0, le=100)
    employee_evaluation: str
    strengths: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    recommended_replies: List[str] = Field(default_factory=list)
