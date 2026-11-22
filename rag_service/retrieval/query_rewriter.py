"""
Query Rewriting Module for Pinecone Hybrid Search.

Improves query retrieval relevance by:
1. Stripping conversational noise, filler words, and interrogatives.
2. Isolating critical domain keywords, technical terms, and acronyms for the BM25 sparse index.
3. Expanding the query with contextual synonyms and structured phrasing for dense embeddings.
4. Optionally leveraging an LLM for advanced reformulation if an API key is configured.
"""

import re
from typing import Tuple, List, Optional
from dataclasses import dataclass

from ..config import settings


# Common conversational noise and stop phrases in user questions
CONVERSATIONAL_PREFIXES = [
    r"^(can|could|would)\s+you\s+(please\s+)?(tell|explain|show|give)\s+(me\s+)?(about\s+)?",
    r"^(i\s+want\s+to\s+know|i\s+would\s+like\s+to\s+know|i\s+am\s+wondering)\s+(about\s+)?",
    r"^(what\s+is|what\s+are|what\s+does|how\s+does|how\s+do|how\s+can\s+i|why\s+is|why\s+are)\s+",
    r"^(please\s+)?(help\s+me\s+)?(find|search|retrieve|get)\s+(information\s+(about|on)\s+)?",
    r"^(tell\s+me\s+about|explain\s+to\s+me)\s+",
]

# Filler terms that dilute vector focus
FILLER_WORDS = {
    "please", "kindly", "basically", "actually", "literally",
    "tell", "explain", "describe", "detail", "details",
    "give", "show", "help", "information", "info", "overview"
}


@dataclass
class RewrittenQuery:
    """Encapsulates the original and improved query representations."""
    original_query: str
    rewritten_query: str
    dense_query: str
    sparse_keywords: str
    extracted_entities: List[str]


class QueryRewriter:
    """Rewrites and optimizes user questions for high-precision hybrid retrieval in Pinecone."""

    def __init__(self, use_llm_if_available: bool = True):
        # Only enable OpenAI LLM if a genuine OpenAI key is provided (not a Groq 'gsk_' or placeholder key)
        valid_openai_key = bool(settings.openai_api_key) and not settings.openai_api_key.startswith("gsk_") and not settings.openai_api_key.startswith("your_")
        self.use_llm = use_llm_if_available and valid_openai_key
        self._llm_chain = None
        if self.use_llm:
            self._init_llm_chain()

    def _init_llm_chain(self):
        """Initializes a fast LangChain prompt chain for model-driven query reformulation."""
        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser
            from langchain_openai import ChatOpenAI

            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are an expert search engine query optimizer. "
                    "Your job is to rewrite the user's conversational question into a concise, "
                    "highly specific search query optimized for vector and keyword hybrid retrieval. "
                    "Remove conversational filler, preserve all technical terms, error codes, and key entities. "
                    "Output ONLY the rewritten search query with no additional text or quotes."
                )),
                ("human", "{question}"),
            ])
            llm = ChatOpenAI(
                model=settings.openai_model_name,
                temperature=0.0,
                openai_api_key=settings.openai_api_key,
                max_tokens=60,
                base_url=""
            )
            self._llm_chain = prompt | llm | StrOutputParser()
        except Exception as e:
            print(f"Warning: Failed to initialize LLM query rewriter chain ({e}), falling back to rule-based.")
            self._llm_chain = None

    def rewrite(self, query: str) -> RewrittenQuery:
        """Rewrites the query using either LLM (if available) or rule-based NLP optimization."""
        cleaned = query.strip()
        if not cleaned:
            return RewrittenQuery(
                original_query="",
                rewritten_query="",
                dense_query="",
                sparse_keywords="",
                extracted_entities=[],
            )

        # 1. Rule-based extraction and cleaning
        extracted_entities = self._extract_key_entities(cleaned)
        rule_rewritten, sparse_kw = self._rule_based_rewrite(cleaned, extracted_entities)

        # 2. If LLM chain is available, use it for the dense semantic query
        if self._llm_chain is not None:
            try:
                llm_rewritten = self._llm_chain.invoke({"question": cleaned}).strip()
                if llm_rewritten and len(llm_rewritten) > 3:
                    return RewrittenQuery(
                        original_query=cleaned,
                        rewritten_query=llm_rewritten,
                        dense_query=llm_rewritten,
                        sparse_keywords=sparse_kw or llm_rewritten,
                        extracted_entities=extracted_entities,
                    )
            except Exception as e:
                print(f"Warning: LLM query rewrite failed: {e}. Using rule-based rewrite.")

        # Default: Rule-based rewritten query
        return RewrittenQuery(
            original_query=cleaned,
            rewritten_query=rule_rewritten,
            dense_query=rule_rewritten,
            sparse_keywords=sparse_kw,
            extracted_entities=extracted_entities,
        )

    def _extract_key_entities(self, text: str) -> List[str]:
        """Extracts technical terms, camelCase words, capitalized names, acronyms, and quoted terms."""
        entities = []

        # Quoted terms: "dotproduct", 'BM25'
        quotes = re.findall(r'["\']([^"\']+)["\']', text)
        entities.extend(quotes)

        # Mixed-case, CamelCase, PascalCase, or Alphanumeric Acronyms (e.g. BM25Encoder, PydanticOutputParser, FastAPI)
        mixed_case = re.findall(r'\b[A-Za-z0-9]*(?:[a-z][A-Z]|[A-Z]{2,}[a-z]|[a-zA-Z]+[0-9]+|[0-9]+[a-zA-Z]+)[A-Za-z0-9]*\b', text)
        entities.extend(mixed_case)

        # Capitalized Proper Nouns / Technical System Names (e.g. Pinecone, LangChain)
        proper_nouns = re.findall(r'\b[A-Z][a-z0-9]{2,}\b', text)
        entities.extend(proper_nouns)

        # Pure Uppercase acronyms (e.g., RAG, BM25, PDF, LLM, API, JSON)
        acronyms = re.findall(r'\b[A-Z0-9]{2,}\b', text)
        entities.extend(acronyms)

        # Code or snake_case terms (e.g., text_embedding, dotproduct)
        code_terms = re.findall(r'\b[a-z0-9]+_[a-z0-9_]+\b', text)
        entities.extend(code_terms)

        # Known vector / database technical terms
        domain_terms = ["dotproduct", "serverless", "cosine", "euclidean", "hybrid", "bm25", "dense", "sparse"]
        text_lower = text.lower()
        for term in domain_terms:
            if re.search(r'\b' + re.escape(term) + r'\b', text_lower):
                entities.append(term)

        # Deduplicate while preserving order
        seen = set()
        unique_entities = []
        for e in entities:
            if e.lower() not in seen:
                seen.add(e.lower())
                unique_entities.append(e)

        return unique_entities

    def _rule_based_rewrite(self, query: str, entities: List[str]) -> Tuple[str, str]:
        """Cleans conversational noise, strips punctuation, and builds dense & sparse queries."""
        text = query.strip()

        # Remove common conversational prefixes
        for pattern in CONVERSATIONAL_PREFIXES:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

        # Remove trailing question marks and punctuation
        text = re.sub(r"[?!.,;]+$", "", text).strip()

        # Tokenize and filter out pure filler words
        tokens = text.split()
        filtered_tokens = [
            t for t in tokens
            if t.lower() not in FILLER_WORDS or t in entities
        ]

        cleaned_text = " ".join(filtered_tokens) if filtered_tokens else text

        # Build sparse keywords string (emphasizing key entities)
        sparse_parts = list(entities)
        for token in filtered_tokens:
            clean_token = re.sub(r'^[^\w]+|[^\w]+$', '', token)
            if clean_token and clean_token.lower() not in [e.lower() for e in sparse_parts]:
                sparse_parts.append(clean_token)

        sparse_keywords = " ".join(sparse_parts)

        return cleaned_text, sparse_keywords
