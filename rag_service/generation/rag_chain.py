"""
LangChain RAG Chain with Hybrid Search and Output Parsers.

Supports:
- Structured Pydantic output parsing (validated citations, confidence score, follow-ups)
- String text output parsing
- Mock LLM generator for offline testing
"""

from typing import List, Dict, Any, Union, Optional
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnablePassthrough
try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

from ..config import settings
from ..parsers.output_parsers import (
    RAGResponse,
    Citation,
    rag_pydantic_parser,
    rag_string_parser,
    get_format_instructions,
)
from ..retrieval.hybrid_retriever import PineconeHybridRetriever, HybridSearchResult


def format_retrieved_documents(docs: Union[List[Document], List[HybridSearchResult]]) -> str:
    """Formats retrieved chunks into numbered context blocks with metadata for the LLM."""
    formatted_chunks = []
    for i, doc in enumerate(docs, 1):
        if isinstance(doc, HybridSearchResult):
            source = doc.metadata.get("source", "unknown")
            chunk_id = doc.id
            score = f"{doc.score:.4f}"
            content = doc.content
        else:
            source = doc.metadata.get("source", "unknown")
            chunk_id = doc.metadata.get("chunk_id", doc.metadata.get("id", f"chunk_{i}"))
            score = f"{doc.metadata.get('hybrid_score', 0.0):.4f}"
            content = doc.page_content

        chunk_header = f"[Source: {source} | Chunk ID: {chunk_id} | Hybrid Score: {score}]"
        formatted_chunks.append(f"{chunk_header}\n{content.strip()}")

    return "\n\n---\n\n".join(formatted_chunks)


STRUCTURED_SYSTEM_PROMPT = """You are a precise, factual AI research assistant.
Answer the user's question using ONLY the retrieved document context provided below.

Strict Guidelines:
1. Ground every claim directly in the provided context passages.
2. In the citations list, cite the specific Source, Chunk ID, and exact supporting quote.
3. Assign a realistic confidence score (0.0 to 1.0) based on how comprehensively the context addresses the question.
4. Suggest 2-3 logical, insightful follow-up questions.
5. If the context does not contain sufficient information, state that clearly and assign a low confidence score.

{format_instructions}
"""

TEXT_SYSTEM_PROMPT = """You are a helpful, accurate AI research assistant.
Answer the user's question clearly and concisely based on the following retrieved context.
If the context does not provide the answer, acknowledge that honestly.
"""


class MockLLM:
    """Offline mock LLM for testing RAG execution without OpenAI API keys."""

    def __init__(self, structured: bool = True):
        self.structured = structured

    def invoke(self, formatted_prompt: Any) -> Union[RAGResponse, str]:
        # Extract question and context from the prompt string representation
        prompt_str = str(formatted_prompt)

        return RAGResponse(
            answer="[Mock LLM Response] Successfully retrieved relevant passages via Pinecone Hybrid Search. "
                   "The dense vectors captured semantic intent while BM25 sparse vectors captured exact keyword matches.",
            citations=[
                Citation(
                    source="sample_doc",
                    chunk_id="chunk_0",
                    snippet="Hybrid search combines dense semantic retrieval with sparse keyword matching.",
                    relevance="Explains hybrid retrieval concept"
                )
            ],
            confidence_score=0.95,
            follow_up_questions=[
                "How do I adjust the alpha parameter to balance keyword vs semantic search?",
                "How does Pinecone's dotproduct metric handle hybrid search scaling?",
            ],
        ) if self.structured else (
            "[Mock LLM Response] The hybrid search pipeline successfully retrieved the relevant context "
            "using Pinecone dense + BM25 sparse representations."
        )


class RAGChain:
    """End-to-end RAG Chain combining Pinecone Hybrid Retriever,

    Prompt Templates, and LangChain Output Parsers.
    """

    def __init__(
        self,
        retriever: PineconeHybridRetriever,
        llm: Any = None,
        structured: bool = True,
        mock_mode: Optional[bool] = None,
    ):
        self.retriever = retriever
        self.structured = structured

        has_llm_key = bool(settings.groq_api_key or settings.openai_api_key)
        if mock_mode is None:
            self.mock_mode = False if has_llm_key else True
        else:
            self.mock_mode = mock_mode

        # Setup Live LLM or Mock
        if llm is not None:
            self.llm = llm
            self.mock_mode = False
        elif not self.mock_mode and settings.groq_api_key and ChatGroq is not None:
            vlm_model = settings.groq_vlm_model or "qwen/qwen3.8-27b"
            groq_model = "qwen/qwen3.8-27b" if "qwen" in vlm_model else vlm_model
            self.llm = ChatGroq(
                model=groq_model,
                temperature=0.0,
                api_key=settings.groq_api_key,
            )
        elif not self.mock_mode and settings.openai_api_key and ChatOpenAI is not None:
            self.llm = ChatOpenAI(
                model=settings.openai_model_name,
                temperature=0.0,
                openai_api_key=settings.openai_api_key,
            )
        elif not self.mock_mode:
            # Production enforcement: do not silently switch to MockLLM
            raise RuntimeError(
                "Production Mode Error: Live LLM inference provider (Groq or OpenAI) is required. "
                "No valid API key or library found, and mock responses are disabled."
            )
        else:
            self.llm = MockLLM(structured=structured)

        # Setup Parser & Prompts
        if self.structured:
            self.parser = rag_pydantic_parser
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", STRUCTURED_SYSTEM_PROMPT),
                ("human", "Context:\n{context}\n\nQuestion: {question}"),
            ]).partial(format_instructions=get_format_instructions())
        else:
            self.parser = rag_string_parser
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", TEXT_SYSTEM_PROMPT),
                ("human", "Context:\n{context}\n\nQuestion: {question}"),
            ])

    def query(
        self,
        question: str,
        alpha: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Runs the complete RAG pipeline:

        1. Hybrid Search (retrieves top_k chunks with alpha weighting)
        2. Context formatting
        3. Prompt synthesis & LLM call
        4. LangChain Output Parser validation
        """
        # 1. Retrieve chunks via hybrid search
        retrieved_results = self.retriever.hybrid_search(question, alpha=alpha, top_k=top_k)
        formatted_context = format_retrieved_documents(retrieved_results)

        # 2. Invoke LLM with Output Parser
        if self.mock_mode:
            parsed_output = self.llm.invoke(formatted_context)
        else:
            # LangChain LCEL sequence: prompt -> llm -> parser
            chain = self.prompt | self.llm | self.parser
            parsed_output = chain.invoke({
                "context": formatted_context,
                "question": question,
            })

        return {
            "question": question,
            "alpha": alpha if alpha is not None else self.retriever.alpha,
            "retrieved_chunks": [r.to_document() for r in retrieved_results],
            "response": parsed_output,
        }
