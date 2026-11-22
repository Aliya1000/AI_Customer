"""
Pinecone Hybrid Search Retriever.

Combines Dense (OpenAI) and Sparse (BM25) vector retrieval with alpha blending.
Implements LangChain's BaseRetriever interface for seamless LCEL integration.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import math

from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_openai import OpenAIEmbeddings
from pydantic import Field, ConfigDict

from ..config import settings
from .bm25_sparse import BM25SparseEncoder
from .embeddings import get_dense_embedder


@dataclass
class HybridSearchResult:
    """Represents a single retrieved document chunk from hybrid search."""
    id: str
    score: float
    content: str
    metadata: Dict[str, Any]

    def to_document(self) -> Document:
        meta = dict(self.metadata)
        meta["id"] = self.id
        meta["hybrid_score"] = self.score
        return Document(page_content=self.content, metadata=meta)


def scale_hybrid_vectors(
    dense_vector: List[float],
    sparse_vector: Dict[str, Any],
    alpha: float,
) -> tuple[List[float], Dict[str, Any]]:
    """Applies convex combination scaling (alpha) to dense and sparse vectors:

    scaled_dense = alpha * dense
    scaled_sparse = (1 - alpha) * sparse

    - alpha = 1.0 -> Pure dense (semantic search)
    - alpha = 0.0 -> Pure sparse (BM25 keyword search)
    - alpha = 0.5 -> Equal weighting
    """
    if not (0.0 <= alpha <= 1.0):
        raise ValueError(f"Alpha must be between 0.0 and 1.0, got {alpha}")

    scaled_dense = [v * alpha for v in dense_vector]
    scaled_sparse = {
        "indices": list(sparse_vector.get("indices", [])),
        "values": [v * (1.0 - alpha) for v in sparse_vector.get("values", [])],
    }
    return scaled_dense, scaled_sparse


class InMemoryVectorStore:
    """Mock vector store for offline testing and verification when live Pinecone credentials

    are not configured.
    """
    def __init__(self):
        self.vectors: Dict[str, Dict[str, Any]] = {}

    def upsert(self, records: List[Dict[str, Any]]) -> None:
        for r in records:
            self.vectors[r["id"]] = r

    def query(
        self,
        vector: List[float],
        sparse_vector: Dict[str, Any],
        top_k: int = 5,
        **kwargs,
    ) -> Dict[str, Any]:
        """Calculates dot product similarity for both dense and sparse components."""
        matches = []
        sparse_map = dict(zip(sparse_vector.get("indices", []), sparse_vector.get("values", [])))

        for vid, item in self.vectors.items():
            # Dense dot product
            dense_score = 0.0
            item_dense = item.get("values", [])
            if vector and item_dense:
                dense_score = sum(q * d for q, d in zip(vector, item_dense))

            # Sparse dot product
            sparse_score = 0.0
            item_sparse = item.get("sparse_values", {})
            if sparse_map and item_sparse:
                item_indices = item_sparse.get("indices", [])
                item_vals = item_sparse.get("values", [])
                for idx, val in zip(item_indices, item_vals):
                    if idx in sparse_map:
                        sparse_score += sparse_map[idx] * val

            total_score = dense_score + sparse_score
            matches.append({
                "id": vid,
                "score": total_score,
                "metadata": item.get("metadata", {}),
            })

        # Sort descending by score
        matches.sort(key=lambda x: x["score"], reverse=True)
        return {"matches": matches[:top_k]}


class PineconeHybridRetriever(BaseRetriever):
    """LangChain-compatible Hybrid Retriever supporting Pinecone serverless/pod indexes

    and in-memory fallback.
    """

    index_name: str = Field(default_factory=lambda: settings.pinecone_index_name)
    alpha: float = Field(default_factory=lambda: settings.hybrid_alpha)
    top_k: int = Field(default_factory=lambda: settings.top_k)

    # Internal components
    _pinecone_index: Any = None
    _bm25_encoder: Optional[BM25SparseEncoder] = None
    _dense_embedder: Any = None
    _mock_store: Optional[InMemoryVectorStore] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(
        self,
        pinecone_index: Any = None,
        bm25_encoder: Optional[BM25SparseEncoder] = None,
        dense_embedder: Any = None,
        alpha: Optional[float] = None,
        top_k: Optional[int] = None,
        mock_mode: bool = False,
        **kwargs,
    ):
        super().__init__(
            alpha=alpha if alpha is not None else settings.hybrid_alpha,
            top_k=top_k if top_k is not None else settings.top_k,
            **kwargs,
        )
        self._bm25_encoder = bm25_encoder or BM25SparseEncoder()

        # Initialize dense embedder (NVIDIA Inference or fallback)
        if dense_embedder is not None:
            self._dense_embedder = dense_embedder
        else:
            self._dense_embedder = get_dense_embedder(mock_mode=mock_mode)

        # Pinecone index or mock store
        if mock_mode or not settings.pinecone_api_key:
            self._mock_store = InMemoryVectorStore()
            self._pinecone_index = None
        else:
            self._pinecone_index = pinecone_index
            self._mock_store = None

    def _get_dense_embedding(self, text: str) -> List[float]:
        """Embeds text using OpenAI embeddings or deterministic fallback."""
        if self._dense_embedder is not None:
            return self._dense_embedder.embed_query(text)

        # Deterministic pseudo-embedding for testing without OpenAI API key
        dim = settings.embedding_dimension
        words = text.lower().split()
        vec = [0.0] * dim
        for i, word in enumerate(words):
            idx = abs(hash(word)) % dim
            vec[idx] += 1.0 / (i + 1)
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def hybrid_search(
        self,
        query: str,
        alpha: Optional[float] = None,
        top_k: Optional[int] = None,
        filter_dict: Optional[Dict[str, Any]] = None,
    ) -> List[HybridSearchResult]:
        """Executes Pinecone hybrid query with alpha scaling."""
        chosen_alpha = self.alpha if alpha is None else alpha
        chosen_top_k = self.top_k if top_k is None else top_k

        # 1. Encode dense and sparse query representations
        dense_vec = self._get_dense_embedding(query)
        sparse_vec = self._bm25_encoder.encode_queries(query)

        # 2. Scale vectors based on hybrid alpha parameter
        scaled_dense, scaled_sparse = scale_hybrid_vectors(dense_vec, sparse_vec, chosen_alpha)

        # 3. Query index (Pinecone live or mock store)
        if self._pinecone_index is not None:
            query_kwargs: Dict[str, Any] = {
                "vector": scaled_dense,
                "sparse_vector": scaled_sparse,
                "top_k": chosen_top_k,
                "include_metadata": True,
            }
            if filter_dict:
                query_kwargs["filter"] = filter_dict
            raw_response = self._pinecone_index.query(**query_kwargs)
        elif self._mock_store is not None:
            raw_response = self._mock_store.query(
                vector=scaled_dense,
                sparse_vector=scaled_sparse,
                top_k=chosen_top_k,
            )
        else:
            raise RuntimeError("Neither Pinecone index nor mock store is initialized.")

        # 4. Format results
        results = []
        for match in raw_response.get("matches", []):
            meta = match.get("metadata", {})
            content = meta.get("text") or meta.get("content") or ""
            results.append(
                HybridSearchResult(
                    id=match["id"],
                    score=float(match.get("score", 0.0)),
                    content=content,
                    metadata=meta,
                )
            )
        return results

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        """LangChain BaseRetriever interface implementation."""
        results = self.hybrid_search(query)
        return [r.to_document() for r in results]
