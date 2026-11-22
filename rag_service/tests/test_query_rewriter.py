"""
Tests for Query Rewriter module.
"""

from rag_service.retrieval.query_rewriter import QueryRewriter


def test_query_rewriter_rule_based():
    rewriter = QueryRewriter(use_llm_if_available=False)

    raw_query = "Can you please tell me how does Pinecone handle the dotproduct distance metric and scaling?"
    result = rewriter.rewrite(raw_query)

    assert result.original_query == raw_query
    # Conversational prefix removed
    assert not result.rewritten_query.lower().startswith("can you please tell me")
    # Technical terms preserved
    assert "dotproduct" in result.rewritten_query.lower() or "dotproduct" in result.sparse_keywords.lower()
    assert "pinecone" in result.rewritten_query.lower()
    # Entity extraction
    assert "dotproduct" in result.extracted_entities or "Pinecone" in result.extracted_entities


def test_query_rewriter_entities():
    rewriter = QueryRewriter(use_llm_if_available=False)

    query = "Why does PydanticOutputParser fail when parsing schema with BM25Encoder?"
    result = rewriter.rewrite(query)

    assert "PydanticOutputParser" in result.extracted_entities
    assert "BM25Encoder" in result.extracted_entities
    assert "PydanticOutputParser" in result.sparse_keywords


def test_query_rewriter_empty():
    rewriter = QueryRewriter(use_llm_if_available=False)
    result = rewriter.rewrite("   ")
    assert result.original_query == ""
    assert result.rewritten_query == ""
