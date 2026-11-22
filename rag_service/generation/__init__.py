"""
Generation module: LangChain Prompt Templates, LLM Chains, and Output Parsing.
"""

from .rag_chain import RAGChain, format_retrieved_documents

__all__ = ["RAGChain", "format_retrieved_documents"]
