# Hybrid Search in Retrieval-Augmented Generation (RAG)

## Overview
Hybrid search combines two complementary retrieval paradigms:
1. **Dense Retrieval**: Utilizes deep learning embedding models (e.g., text-embedding-3-small, sentence-transformers) to capture high-dimensional semantic relationships, synonyms, and conceptual intent.
2. **Sparse Retrieval**: Utilizes inverted-index lexical scoring algorithms like BM25 or learned sparse representations (SPLADE) to capture exact keyword matches, domain terminology, technical codes, and entity names.

## The Alpha Parameter Convex Combination
In Pinecone hybrid search, dense and sparse vectors are combined into a single query using a convex weighting factor $\alpha \in [0.0, 1.0]$:

$$\vec{v}_{\text{dense\_scaled}} = \alpha \cdot \vec{v}_{\text{dense}}$$
$$\vec{v}_{\text{sparse\_scaled}} = (1 - \alpha) \cdot \vec{v}_{\text{sparse}}$$

- When $\alpha = 1.0$: The system performs pure dense (semantic) retrieval. Useful for open-ended queries with semantic ambiguity.
- When $\alpha = 0.0$: The system performs pure sparse (BM25 lexical) retrieval. Useful for finding specific serial numbers, error codes (e.g. `ERR_404_NOT_FOUND`), or rare product SKU identifiers.
- When $\alpha = 0.5$: Balanced hybrid retrieval, providing optimal performance across diverse query distributions.

## Pinecone Metric Configuration
Pinecone requires the index distance metric to be set to `dotproduct` when conducting hybrid search. Under the dotproduct metric, the combined score equals the sum of the dense dot product and sparse dot product.
