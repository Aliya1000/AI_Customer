"""
LangChain Output Parsers.

Provides:
1. PydanticOutputParser for structured RAG responses with validated citations,
   confidence scores, and follow-up questions.
2. StrOutputParser for standard text output.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser


class Citation(BaseModel):
    """Citation referencing a specific chunk or document source."""
    source: str = Field(description="Filename or identifier of the source document")
    snippet: str = Field(description="Exact or summarized quote supporting the assertion")
    chunk_id: Optional[str] = Field(default=None, description="Identifier of the retrieved chunk if available")
    relevance: Optional[str] = Field(default=None, description="Brief explanation of why this source is relevant")


class RAGResponse(BaseModel):
    """Structured response model parsed by LangChain's PydanticOutputParser."""
    answer: str = Field(
        description="Comprehensive, accurate, factual answer synthesizing the retrieved context"
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="List of verified citations from the retrieved documents supporting the answer"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0 based on how well the context answered the question"
    )
    follow_up_questions: List[str] = Field(
        default_factory=list,
        description="2-3 relevant follow-up questions the user might ask next"
    )


# LangChain Parsers
rag_pydantic_parser = PydanticOutputParser(pydantic_object=RAGResponse)
rag_string_parser = StrOutputParser()


def get_format_instructions() -> str:
    """Returns formatting instructions for the Pydantic parser to inject into prompts."""
    return rag_pydantic_parser.get_format_instructions()
