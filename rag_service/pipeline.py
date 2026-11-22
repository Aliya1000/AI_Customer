"""
Unified Hybrid RAG Pipeline orchestrator.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any, Union

from langchain_core.documents import Document

from .config import settings
from .parsers.document_parsers import DocumentIngestionPipeline
from .parsers.output_parsers import RAGResponse
from .retrieval.bm25_sparse import BM25SparseEncoder
from .retrieval.hybrid_retriever import PineconeHybridRetriever, HybridSearchResult
from .indexing.indexer import PineconeHybridIndexer
from .generation.rag_chain import RAGChain


class HybridRAGPipeline:
    """End-to-End RAG Pipeline using Pinecone Hybrid Search and LangChain Parsers."""

    def __init__(
        self,
        mock_mode: Optional[bool] = None,
        alpha: Optional[float] = None,
        top_k: Optional[int] = None,
    ):
        # Auto-detect mock mode if Pinecone API key is missing
        if mock_mode is None:
            self.mock_mode = not bool(settings.pinecone_api_key)
        else:
            self.mock_mode = mock_mode

        self.alpha = alpha if alpha is not None else settings.hybrid_alpha
        self.top_k = top_k if top_k is not None else settings.top_k

        # 1. Document Ingestion Parser
        self.ingestion = DocumentIngestionPipeline()

        # 2. BM25 Sparse Encoder
        self.bm25_encoder = BM25SparseEncoder()

        # 3. Pinecone Indexer
        self.indexer = PineconeHybridIndexer(
            bm25_encoder=self.bm25_encoder,
            mock_mode=self.mock_mode,
        )

        # 4. Pinecone Hybrid Retriever
        self.retriever = PineconeHybridRetriever(
            pinecone_index=self.indexer.index,
            bm25_encoder=self.bm25_encoder,
            alpha=self.alpha,
            top_k=self.top_k,
            mock_mode=self.mock_mode,
        )

        # Link mock stores if in mock mode
        if self.mock_mode and self.indexer.mock_store is not None:
            self.retriever._mock_store = self.indexer.mock_store

    def ingest_files(self, paths: Union[str, Path, List[Union[str, Path]]]) -> int:
        """Loads files using LangChain loaders/parsers, splits into chunks,

        and indexes into Pinecone with dense + sparse vectors.
        """
        if isinstance(paths, (str, Path)):
            paths = [paths]

        all_chunks: List[Document] = []
        for path in paths:
            p = Path(path)
            if p.is_dir():
                chunks = self.ingestion.process_directory(p)
            else:
                chunks = self.ingestion.process_file(p)
            all_chunks.extend(chunks)

        print(f"Parsed {len(all_chunks)} chunks from {len(paths)} file/directory targets.")
        upserted_count = self.indexer.index_documents(all_chunks)
        return upserted_count

    def search(
        self,
        query: str,
        alpha: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> List[HybridSearchResult]:
        """Performs raw hybrid search without calling the LLM generation step."""
        return self.retriever.hybrid_search(
            query=query,
            alpha=alpha if alpha is not None else self.alpha,
            top_k=top_k if top_k is not None else self.top_k,
        )

    def query(
        self,
        question: str,
        alpha: Optional[float] = None,
        top_k: Optional[int] = None,
        structured: bool = True,
    ) -> Dict[str, Any]:
        """Runs the full RAG pipeline:

        - Retrieves relevant chunks via Pinecone Hybrid Search (alpha weighted)
        - Synthesizes answer using LangChain Prompt Template + LLM
        - Parses answer into structured Pydantic object (or string) using LangChain Output Parser
        """
        chain = RAGChain(
            retriever=self.retriever,
            structured=structured,
            mock_mode=self.mock_mode,
        )
        return chain.query(question=question, alpha=alpha, top_k=top_k)
