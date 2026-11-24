"""
Pinecone Hybrid Indexer.

Handles:
1. Pinecone index creation and connection with `dotproduct` metric (mandatory for hybrid search).
2. Fitting BM25 sparse encoder on the document corpus and persisting parameters.
3. Batching dense and sparse embeddings.
4. Upserting hybrid records with metadata into Pinecone (or in-memory mock store).
"""

import logging
import math
from typing import List, Optional, Any, Dict
from pinecone import Pinecone, ServerlessSpec
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from ..config import settings
from ..retrieval.bm25_sparse import BM25SparseEncoder
from ..retrieval.hybrid_retriever import InMemoryVectorStore
from ..retrieval.embeddings import get_dense_embedder

logger = logging.getLogger(__name__)


class PineconeHybridIndexer:
    """Manages document chunking, sparse/dense vector generation,

    and batch upserts to Pinecone.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        index_name: Optional[str] = None,
        bm25_encoder: Optional[BM25SparseEncoder] = None,
        dense_embedder: Any = None,
        mock_mode: bool = False,
    ):
        self.api_key = api_key or settings.pinecone_api_key
        self.index_name = index_name or settings.pinecone_index_name
        self.mock_mode = mock_mode or not bool(self.api_key)

        self.bm25_encoder = bm25_encoder or BM25SparseEncoder()
        self.mock_store: Optional[InMemoryVectorStore] = InMemoryVectorStore() if self.mock_mode else None

        # Setup Dense Embedder (NVIDIA Inference or fallback)
        if dense_embedder is not None:
            self.dense_embedder = dense_embedder
        else:
            self.dense_embedder = get_dense_embedder(mock_mode=self.mock_mode)

        self.pinecone_client: Optional[Pinecone] = None
        self.index: Any = None

        if not self.mock_mode:
            self._init_pinecone()

    def _init_pinecone(self) -> None:
        """Initializes Pinecone client and creates index if it does not exist."""
        try:
            self.pinecone_client = Pinecone(api_key=self.api_key)

            # Check existing indexes
            existing_indexes = [idx["name"] for idx in self.pinecone_client.list_indexes()]

            if self.index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index '{self.index_name}' with metric='dotproduct'...")
                # Note: dotproduct metric is required for hybrid search to correctly combine dense and sparse scores
                self.pinecone_client.create_index(
                    name=self.index_name,
                    dimension=settings.embedding_dimension,
                    metric="dotproduct",
                    spec=ServerlessSpec(
                        cloud=settings.pinecone_cloud,
                        region=settings.pinecone_region,
                    ),
                )

            self.index = self.pinecone_client.Index(self.index_name)
        except Exception as e:
            logger.warning(f"Could not connect to Pinecone ({e}); switching to local vector store.")
            self.mock_mode = True
            if self.mock_store is None:
                self.mock_store = InMemoryVectorStore()
            self.index = None

    def _get_dense_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Computes dense embeddings for a batch of text chunks."""
        if self.dense_embedder is not None:
            return self.dense_embedder.embed_documents(texts)

        # Fallback deterministic embeddings for testing/mock mode
        embeddings = []
        dim = settings.embedding_dimension
        for text in texts:
            words = text.lower().split()
            vec = [0.0] * dim
            for i, word in enumerate(words):
                idx = abs(hash(word)) % dim
                vec[idx] += 1.0 / (i + 1)
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            embeddings.append([x / norm for x in vec])
        return embeddings

    def index_documents(
        self,
        documents: List[Document],
        batch_size: int = 100,
        fit_bm25: bool = True,
    ) -> int:
        """Indexes LangChain documents into Pinecone with both dense and sparse representations."""
        if not documents:
            return 0

        corpus_texts = [doc.page_content for doc in documents]

        # 1. Fit BM25 on the document corpus if requested
        if fit_bm25:
            print(f"Fitting BM25 sparse model on {len(corpus_texts)} chunks...")
            self.bm25_encoder.fit(corpus_texts)
            self.bm25_encoder.save()

        # 2. Process in batches
        total_upserted = 0
        total_docs = len(documents)

        for i in range(0, total_docs, batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_texts = [d.page_content for d in batch_docs]

            # Generate dense embeddings
            dense_vectors = self._get_dense_embeddings(batch_texts)

            # Generate records with dense and sparse vectors + metadata
            records = []
            for j, doc in enumerate(batch_docs):
                chunk_id = doc.metadata.get("chunk_id") or f"doc_{i + j}"
                sparse_vec = self.bm25_encoder.encode_documents(doc.page_content)

                metadata: Dict[str, Any] = {
                    "text": doc.page_content,
                    **{k: v for k, v in doc.metadata.items() if isinstance(v, (str, int, float, bool))},
                }

                records.append({
                    "id": str(chunk_id),
                    "values": dense_vectors[j],
                    "sparse_values": sparse_vec,
                    "metadata": metadata,
                })

            # Upsert into Pinecone or Mock Store
            if not self.mock_mode and self.index is not None:
                self.index.upsert(vectors=records)
            elif self.mock_store is not None:
                self.mock_store.upsert(records)

            total_upserted += len(records)
            print(f"Upserted batch {i // batch_size + 1}/{(total_docs + batch_size - 1) // batch_size} ({total_upserted}/{total_docs} records)")

        return total_upserted
