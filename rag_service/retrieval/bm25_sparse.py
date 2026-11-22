"""
BM25 Sparse Encoder module for Pinecone Hybrid Search.

Wraps pinecone_text.sparse.BM25Encoder with persistence, corpus-fitting,
and document/query sparse vector generation.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional

from pinecone_text.sparse import BM25Encoder

from ..config import settings


class BM25SparseEncoder:
    """Manages BM25 sparse vector generation for Pinecone hybrid search."""

    def __init__(self, params_path: Optional[str] = None):
        self.params_path = Path(params_path or settings.bm25_params_path)
        self.encoder: BM25Encoder = BM25Encoder()
        self._is_fitted: bool = False
        self._initialize()

    def _initialize(self):
        """Attempts to load saved parameters from disk, or fallback to default cached parameters."""
        # 1. Check specified or settings params path
        candidate_paths = [
            self.params_path,
            settings.data_dir / "bm25_params.json",
            Path("data/bm25_params.json"),
            Path("bm25_params.json"),
        ]
        for p in candidate_paths:
            if p.exists():
                try:
                    self.encoder.load(str(p))
                    self._is_fitted = True
                    return
                except Exception as e:
                    print(f"Warning: Failed to load BM25 params from {p}: {e}")

        # 2. Try default cached params if available
        candidate_defaults = [
            settings.data_dir / "default_bm25_params.json",
            Path("data/default_bm25_params.json"),
            Path("default_bm25_params.json"),
        ]
        for default_params in candidate_defaults:
            if default_params.exists():
                try:
                    self.encoder.load(str(default_params))
                    self._is_fitted = True
                    return
                except Exception as e:
                    print(f"Warning: Failed to load default BM25 params from {default_params}: {e}")

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    def fit(self, texts: List[str]) -> "BM25SparseEncoder":
        """Fits the BM25 model on a corpus of text strings."""
        if not texts:
            raise ValueError("Corpus cannot be empty for BM25 fitting.")
        self.encoder.fit(texts)
        self._is_fitted = True
        return self

    def save(self, path: Optional[str] = None) -> None:
        """Saves current BM25 parameters to a JSON file."""
        target_path = Path(path or self.params_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        self.encoder.dump(str(target_path))

    def encode_documents(self, text: str) -> Dict[str, Any]:
        """Encodes document text into Pinecone sparse vector format:

        {'indices': [int, ...], 'values': [float, ...]}
        """
        if not self._is_fitted:
            # Fallback fit on document if no corpus was fitted
            self.encoder.fit([text])
            self._is_fitted = True

        sparse_dict = self.encoder.encode_documents(text)
        return {
            "indices": [int(idx) for idx in sparse_dict["indices"]],
            "values": [float(val) for val in sparse_dict["values"]],
        }

    def encode_queries(self, query: str) -> Dict[str, Any]:
        """Encodes query string into Pinecone sparse vector format:

        {'indices': [int, ...], 'values': [float, ...]}
        """
        if not self._is_fitted:
            # If completely unfitted, fit on query itself so indices exist
            self.encoder.fit([query])
            self._is_fitted = True

        sparse_dict = self.encoder.encode_queries(query)
        return {
            "indices": [int(idx) for idx in sparse_dict["indices"]],
            "values": [float(val) for val in sparse_dict["values"]],
        }
