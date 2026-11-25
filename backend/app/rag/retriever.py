"""
Hybrid Knowledge Retriever combining Vector Semantic Similarity and BM25 Keyword Search.

Uses Reciprocal Rank Fusion (RRF) to merge dense and sparse rankings for high recall
and precision across technical specifications, pricing figures, and FAQs.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi

from app.rag.ingest import ChromaKnowledgeBase, EmbeddingGenerator

logger = logging.getLogger("voxsell.rag.retriever")


class HybridRetriever:
    """
    Executes hybrid search combining ChromaDB dense vector embeddings and BM25 sparse keyword matching.
    """

    def __init__(self, kb: Optional[ChromaKnowledgeBase] = None):
        self.kb = kb or ChromaKnowledgeBase()
        self.embedder = EmbeddingGenerator()
        self._bm25_corpus: List[List[str]] = []
        self._doc_ids: List[str] = []
        self._doc_texts: List[str] = []
        self._doc_metadatas: List[Dict[str, Any]] = []
        self._bm25_model: Optional[BM25Okapi] = None
        self._sync_bm25_index()

    def _sync_bm25_index(self) -> None:
        """
        Synchronizes the in-memory BM25 index with documents currently stored in ChromaDB.
        """
        data = self.kb.collection.get()
        ids = data.get("ids", [])
        documents = data.get("documents", [])
        metadatas = data.get("metadatas", [])

        if not ids or not documents:
            logger.debug("ChromaDB collection is empty. BM25 index not populated.")
            self._bm25_model = None
            return

        self._doc_ids = ids
        self._doc_texts = documents
        self._doc_metadatas = metadatas or [{} for _ in ids]

        # Tokenize corpus for BM25
        self._bm25_corpus = [
            re.findall(r'\b[a-zA-Z0-9_\$%-]+\b', doc.lower())
            for doc in documents
        ]
        self._bm25_model = BM25Okapi(self._bm25_corpus)
        logger.debug(f"Synchronized BM25 index with {len(ids)} document chunks.")

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Performs hybrid retrieval with Reciprocal Rank Fusion (RRF).

        Args:
            query: The user query string (e.g. "What is the price of starter tier?")
            top_k: Number of combined results to return (default: 4)

        Returns:
            List of ranked result dicts with 'id', 'text', 'metadata', 'score'.
        """
        cleaned_query = query.strip()
        if not cleaned_query:
            return []

        # Ensure BM25 has data
        if not self._bm25_model:
            self._sync_bm25_index()
            if not self._bm25_model:
                return []

        # 1. Dense Vector Search (ChromaDB)
        query_embedding = self.embedder.generate_embeddings([cleaned_query])
        vec_results = self.kb.collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k * 2, len(self._doc_ids)),
        )

        vector_ranks: Dict[str, int] = {}
        if vec_results and vec_results.get("ids") and vec_results["ids"][0]:
            for rank, doc_id in enumerate(vec_results["ids"][0]):
                vector_ranks[doc_id] = rank + 1

        # 2. Sparse BM25 Search
        query_tokens = re.findall(r'\b[a-zA-Z0-9_\$%-]+\b', cleaned_query.lower())
        bm25_scores = self._bm25_model.get_scores(query_tokens)

        # Sort BM25 by score descending
        bm25_ranked_indices = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True
        )[:top_k * 2]

        bm25_ranks: Dict[str, int] = {}
        for rank, idx in enumerate(bm25_ranked_indices):
            doc_id = self._doc_ids[idx]
            bm25_ranks[doc_id] = rank + 1

        # 3. Reciprocal Rank Fusion (RRF)
        all_candidate_ids = set(vector_ranks.keys()).union(set(bm25_ranks.keys()))
        rrf_scores: Dict[str, float] = {}

        rrf_k = 60  # Standard RRF smoothing constant
        for doc_id in all_candidate_ids:
            score = 0.0
            if doc_id in vector_ranks:
                score += 1.0 / (rrf_k + vector_ranks[doc_id])
            if doc_id in bm25_ranks:
                score += 1.0 / (rrf_k + bm25_ranks[doc_id])
            rrf_scores[doc_id] = score

        # Sort candidates by combined RRF score
        sorted_candidates = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        # Map back to document objects
        results = []
        doc_map = {doc_id: (text, meta) for doc_id, text, meta in zip(self._doc_ids, self._doc_texts, self._doc_metadatas)}

        for doc_id, score in sorted_candidates:
            if doc_id in doc_map:
                text, meta = doc_map[doc_id]
                results.append({
                    "id": doc_id,
                    "text": text,
                    "metadata": meta,
                    "score": round(score, 5),
                })

        return results
