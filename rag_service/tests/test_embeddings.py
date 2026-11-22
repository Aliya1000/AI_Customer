"""
Tests for NVIDIA Inference Embeddings integration.
"""

from rag_service.config import settings
from rag_service.retrieval.embeddings import get_dense_embedder


def test_nvidia_embeddings_initialization(monkeypatch):
    monkeypatch.setattr(settings, "nvidia_api_key", "nvapi-mock-test-key")
    monkeypatch.setattr(settings, "nvidia_embedding_model", "nvidia/nv-embedqa-e5-v5")
    monkeypatch.setattr(settings, "nvidia_base_url", "https://integrate.api.nvidia.com/v1")

    embedder = get_dense_embedder(mock_mode=False)
    assert embedder is not None
    assert getattr(embedder, "model", None) == "nvidia/nv-embedqa-e5-v5"


def test_nvidia_embeddings_model_normalization(monkeypatch):
    monkeypatch.setattr(settings, "nvidia_api_key", "nvapi-mock-test-key")
    monkeypatch.setattr(settings, "nvidia_embedding_model", "Nemotron-3.5-Embed-1B")

    embedder = get_dense_embedder(mock_mode=False)
    assert embedder is not None
    assert getattr(embedder, "model", None) == "nvidia/nemotron-3.5-embed-1b"


def test_mock_mode_embeddings():
    embedder = get_dense_embedder(mock_mode=True)
    assert embedder is None


def test_default_embedding_dimension():
    # NVIDIA nv-embedqa-e5-v5 produces 1024-dimensional embeddings
    assert settings.embedding_dimension == 1024


def test_content_safety_screening_fallback():
    from rag_service.retrieval.embeddings import NVIDIAInferenceEmbeddings

    embedder = NVIDIAInferenceEmbeddings(api_key="nvapi-mock-key", dimension=1024)

    def mock_call_api_raw(texts, input_type):
        if len(texts) > 1:
            raise RuntimeError("NVIDIA API error (HTTP 422): input rejected by content safety screening")
        if "flagged" in texts[0]:
            raise RuntimeError("NVIDIA API error (HTTP 422): input rejected by content safety screening")
        return [[0.5] * 1024]

    embedder._call_api_raw = mock_call_api_raw

    # Should not raise RuntimeError; should isolate offending chunk and assign neutral fallback
    embeddings = embedder.embed_documents(["safe chunk", "flagged chunk"])
    assert len(embeddings) == 2
    assert embeddings[0] == [0.5] * 1024
    # Pinecone strictly requires at least one non-zero value in dense vectors
    assert any(x != 0.0 for x in embeddings[1])
    assert len(embeddings[1]) == 1024
