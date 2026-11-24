from typing import List
from pydantic import BaseModel, Field


class Article(BaseModel):
    title: str
    source: str
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    snippet: str


class FAQ(BaseModel):
    question: str
    answer: str


class SupervisorOutput(BaseModel):
    status: str = "Completed"
    active_pattern: str = "Context-Aware LLM + RAG Retrieval"
    agents_completed: int = 6


class QueryAnalysisOutput(BaseModel):
    summary: str
    intent: str
    sentiment: str


class KnowledgeRetrievalOutput(BaseModel):
    summary: str
    articles: List[Article] = Field(default_factory=list)
    faqs: List[FAQ] = Field(default_factory=list)
    troubleshooting_steps: List[str] = Field(default_factory=list)


class ProductInformationOutput(BaseModel):
    product_name: str
    product_category: str
    product_description: str
    warranty_status: str


class ResponseGenerationOutput(BaseModel):
    suggested_response: str


class EvaluationAndCoachingOutput(BaseModel):
    evaluation_score: int = Field(ge=0, le=100)
    tips: List[str] = Field(default_factory=list)


class AgentOutputs(BaseModel):
    supervisor: SupervisorOutput
    query_analysis: QueryAnalysisOutput
    knowledge_retrieval: KnowledgeRetrievalOutput
    product_information: ProductInformationOutput
    response_generation: ResponseGenerationOutput
    evaluation_and_coaching: EvaluationAndCoachingOutput
