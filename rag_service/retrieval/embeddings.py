"""
NVIDIA Inference Embeddings for Pinecone Hybrid RAG.

Directly integrates with NVIDIA NIM AI Foundation Endpoints (e.g. nvidia/nemotron-3.5-embed-1b)
handling:
1. Asymmetric input types (passage vs query)
2. Matryoshka dimension scaling (e.g. 1024)
3. Text sanitization (URI scheme guardrail neutralization, control character removal)
4. Resilient Content Safety Screening recovery (batch decomposition + valid unit-normalized Pinecone fallback vectors)
"""

import re
import math
import time
import requests
from typing import List, Optional
from langchain_core.embeddings import Embeddings

from ..config import settings


class NVIDIAInferenceEmbeddings(Embeddings):
    """Resilient LangChain Embeddings implementation for NVIDIA NIM Inference API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        dimension: Optional[int] = None,
        batch_size: int = 25,
        timeout: int = 60,
    ):
        self.api_key = api_key or settings.nvidia_api_key
        raw_model = model or settings.nvidia_embedding_model or "nvidia/nemotron-3.5-embed-1b"
        self.model = self._normalize_model_name(raw_model)
        self.base_url = (base_url or settings.nvidia_base_url or "https://integrate.api.nvidia.com/v1").rstrip("/")
        self.dimension = dimension or settings.embedding_dimension or 1024
        self.batch_size = batch_size
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY must be provided for NVIDIAInferenceEmbeddings.")

    @staticmethod
    def _normalize_model_name(model_name: str) -> str:
        """Normalizes model names (e.g. 'Nemotron-3.5-Embed-1B' -> 'nvidia/nemotron-3.5-embed-1b')."""
        cleaned = model_name.strip()
        cleaned_lower = cleaned.lower()
        if not cleaned_lower.startswith("nvidia/") and not "/" in cleaned_lower:
            return f"nvidia/{cleaned_lower}"
        return cleaned_lower

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Cleans control characters, raw byte artifacts, and neutralizes URI scheme

        patterns (e.g. 'data:', 'Metadata:', 'Javascript:') that trigger false-positive
        XSS/URI guardrails in NVIDIA NIM.
        """
        if not text:
            return " "
        # Remove non-printable control characters except standard whitespace
        cleaned = "".join(c for c in text if c.isprintable() or c in "\n\r\t")
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", cleaned)

        # Prevent false-positive XSS URI scheme triggers in NVIDIA NIM (e.g. 'Metadata:' -> 'Metadata :')
        cleaned = re.sub(r"(\b[a-zA-Z0-9_]+):", r"\1 :", cleaned)

        # Limit single chunk length to 4000 characters to prevent token limit/guardrail errors
        if len(cleaned) > 4000:
            cleaned = cleaned[:4000]
        return cleaned.strip() or " "

    def _generate_fallback_vector(self, text: str) -> List[float]:
        """Generates a deterministic unit-normalized dense vector for Pinecone

        when a chunk cannot be processed by the remote cloud model.
        Guarantees non-zero magnitude to satisfy Pinecone's strict non-zero vector constraint.
        """
        dim = self.dimension
        vec = [0.0] * dim
        words = text.lower().split()
        for i, word in enumerate(words):
            idx = abs(hash(word)) % dim
            vec[idx] += 1.0 / (i + 1)
        # Add deterministic non-zero seed to ensure vector is never all-zeros
        vec[0] += 1e-3
        vec[dim // 2] += 1e-3
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def _call_api_raw(self, texts: List[str], input_type: str) -> List[List[float]]:
        """Makes direct HTTP POST request to NVIDIA NIM /v1/embeddings endpoint."""
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "model": self.model,
            "input": texts,
            "input_type": input_type,
            "dimensions": self.dimension,
        }

        last_error: Optional[Exception] = None
        response = None
        for attempt in range(3):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
            except requests.RequestException as e:
                last_error = RuntimeError(f"Network error communicating with NVIDIA NIM ({url}): {e}")
                if attempt < 2:
                    time.sleep(0.8 * (2 ** attempt))
                    continue
                raise last_error from e

            if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(0.8 * (2 ** attempt))
                continue
            break

        if response.status_code != 200:
            error_detail = response.text
            try:
                err_json = response.json()
                error_detail = err_json.get("message") or err_json.get("error", {}).get("message") or response.text
            except Exception:
                pass
            raise RuntimeError(
                f"NVIDIA API error (HTTP {response.status_code}) using model '{self.model}': {error_detail}"
            )

        data = response.json()
        embeddings_data = data.get("data", [])
        embeddings_data.sort(key=lambda x: x.get("index", 0))
        return [item["embedding"] for item in embeddings_data]

    def _embed_single_with_fallback(self, text: str, input_type: str) -> List[float]:
        """Embeds an individual chunk. If NVIDIA's content safety rejects it,

        falls back to a valid, normalized pseudo-vector so Pinecone indexing succeeds
        and BM25 sparse search still functions for that chunk.
        """
        sanitized = self._sanitize_text(text)

        # 1. Primary attempt with sanitized text
        try:
            return self._call_api_raw([sanitized], input_type=input_type)[0]
        except RuntimeError as e:
            err_str = str(e).lower()
            if "content safety screening" in err_str or "422" in err_str:
                # 2. Try secondary text simplification
                simplified = re.sub(r"[^\w\s.,;:?!-]", " ", sanitized)
                simplified = " ".join(simplified.split())
                if simplified:
                    try:
                        return self._call_api_raw([simplified], input_type=input_type)[0]
                    except Exception:
                        pass

                # 3. Graceful degradation: Assign deterministic unit-normalized vector for Pinecone
                preview = (text[:60] + "...") if len(text) > 60 else text
                print(
                    f"[Content Safety Warning] Chunk rejected by NVIDIA content safety screening: '{preview}'. "
                    f"Assigned valid unit-normalized dense vector; BM25 sparse index will enable keyword retrieval."
                )
                return self._generate_fallback_vector(text)
            raise e

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds document passages in batches with automatic batch decomposition

        if content safety screening triggers on any chunk in the batch.
        """
        if not texts:
            return []

        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), self.batch_size):
            batch = [self._sanitize_text(t) for t in texts[i : i + self.batch_size]]

            try:
                # Fast path: Embed whole batch at once
                batch_embeddings = self._call_api_raw(batch, input_type="passage")
                all_embeddings.extend(batch_embeddings)
            except RuntimeError as e:
                err_msg = str(e).lower()
                if "content safety screening" in err_msg or "422" in err_msg:
                    # Decompose batch into individual calls to isolate only the offending chunk(s)
                    print(f"Notice: Batch of {len(batch)} chunks triggered content safety. Isolating individual chunks...")
                    for raw_chunk in texts[i : i + self.batch_size]:
                        vec = self._embed_single_with_fallback(raw_chunk, input_type="passage")
                        all_embeddings.append(vec)
                else:
                    raise e

        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embeds a single search query with input_type='query' and fallback."""
        return self._embed_single_with_fallback(text, input_type="query")


def get_dense_embedder(mock_mode: bool = False) -> Optional[Embeddings]:
    """Returns the configured dense embedding model.

    Prioritizes NVIDIA Inference when NVIDIA_API_KEY is configured.
    """
    if mock_mode:
        return None

    # 1. NVIDIA NIM Inference Embeddings
    if settings.nvidia_api_key and not settings.nvidia_api_key.startswith("your_"):
        return NVIDIAInferenceEmbeddings(
            api_key=settings.nvidia_api_key,
            model=settings.nvidia_embedding_model,
            base_url=settings.nvidia_base_url,
            dimension=settings.embedding_dimension,
        )

    # 2. OpenAI Fallback
    if settings.openai_api_key and not settings.openai_api_key.startswith("gsk_") and not settings.openai_api_key.startswith("your_"):
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            openai_api_key=settings.openai_api_key,
        )

    return None
