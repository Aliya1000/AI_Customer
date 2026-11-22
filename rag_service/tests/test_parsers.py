"""
Tests for LangChain Document Parsers and Output Parsers.
"""

import pytest
from pathlib import Path
from langchain_core.documents import Document

from rag_service.parsers.document_parsers import DocumentIngestionPipeline
from rag_service.parsers.output_parsers import (
    RAGResponse,
    Citation,
    rag_pydantic_parser,
    get_format_instructions,
)


def test_document_ingestion_text(tmp_path: Path):
    test_file = tmp_path / "sample.txt"
    test_file.write_text("Hello world! This is a test document for LangChain parsing.\nSecond paragraph here.")

    pipeline = DocumentIngestionPipeline(chunk_size=50, chunk_overlap=10)
    docs = pipeline.load_file(test_file)
    assert len(docs) == 1
    assert docs[0].metadata["source"] == "sample.txt"

    chunks = pipeline.split_documents(docs)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert "chunk_id" in chunk.metadata
        assert "char_count" in chunk.metadata


def test_document_ingestion_json(tmp_path: Path):
    test_file = tmp_path / "sample.json"
    test_file.write_text("""[
        {"title": "Doc 1", "content": "Pinecone hybrid search combines dense and sparse."},
        {"title": "Doc 2", "content": "LangChain output parsers validate LLM output."}
    ]""")

    pipeline = DocumentIngestionPipeline()
    docs = pipeline.load_file(test_file)
    assert len(docs) == 2
    assert "Doc 1" in docs[0].page_content or "dense and sparse" in docs[0].page_content


def test_pydantic_output_parser():
    sample_llm_json = """{
        "answer": "Hybrid search combines dense semantic embeddings with BM25 sparse vectors.",
        "citations": [
            {
                "source": "rag_doc.md",
                "chunk_id": "rag_doc.md_chunk_0",
                "snippet": "Hybrid search combines two complementary retrieval paradigms.",
                "relevance": "Direct definition"
            }
        ],
        "confidence_score": 0.98,
        "follow_up_questions": [
            "What is the alpha parameter?",
            "How does Pinecone compute the dotproduct?"
        ]
    }"""

    parsed: RAGResponse = rag_pydantic_parser.parse(sample_llm_json)
    assert isinstance(parsed, RAGResponse)
    assert "dense semantic embeddings" in parsed.answer
    assert len(parsed.citations) == 1
    assert parsed.citations[0].source == "rag_doc.md"
    assert parsed.confidence_score == 0.98
    assert len(parsed.follow_up_questions) == 2


def test_format_instructions():
    instructions = get_format_instructions()
    assert "answer" in instructions
    assert "citations" in instructions
    assert "confidence_score" in instructions
