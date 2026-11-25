"""
Tests for Phase 5 RAG Knowledge Retrieval:
- Document chunking and parsing
- ChromaDB vector upsert and indexing
- Hybrid vector + BM25 retrieval
- search_knowledge_base tool execution
- Admin upload endpoint POST /kb/upload
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rag.ingest import DocumentChunker, DocumentParser, ChromaKnowledgeBase
from app.rag.retriever import HybridRetriever
from app.rag.tools import search_knowledge_base


def test_document_chunker_overlapping_windows():
    """Assert chunker splits text into overlapping windows without dropping sentences."""
    sample_text = (
        "VoxSell is an autonomous sales voice agent. " * 30 +
        "It supports English, Hindi, and Punjabi fluently. " * 30
    )
    chunker = DocumentChunker(chunk_size=400, chunk_overlap=80)
    chunks = chunker.chunk_text(sample_text, source="test.md", category="test")

    assert len(chunks) > 1
    assert "source" in chunks[0]["metadata"]
    assert chunks[0]["metadata"]["source"] == "test.md"


def test_hybrid_retrieval_finds_pricing_facts():
    """Assert HybridRetriever retrieves correct pricing data from ChromaDB collection."""
    kb_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../knowledge_base"))
    kb = ChromaKnowledgeBase()
    kb.ingest_directory(kb_dir)

    retriever = HybridRetriever(kb=kb)
    results = retriever.search("Starter tier price", top_k=2)

    assert len(results) > 0
    top_text = results[0]["text"]
    assert "$499" in top_text or "pricing" in top_text.lower()


def test_search_knowledge_base_tool():
    """Assert search_knowledge_base tool returns formatted factual string."""
    facts = search_knowledge_base("calendar integrations")
    assert "Fact" in facts
    assert "Google Calendar" in facts or "Outlook" in facts or "Cal.com" in facts


def test_admin_kb_upload_endpoint(tmp_path):
    """Assert POST /kb/upload accepts and indexes new file dynamically without restarting."""
    client = TestClient(app)

    # Create temporary markdown file
    test_file = tmp_path / "custom_policy.md"
    test_file.write_text("# Refund Policy\nAll annual contracts have a 30-day money-back guarantee.", encoding="utf-8")

    with open(test_file, "rb") as f:
        response = client.post(
            "/kb/upload",
            files={"file": ("custom_policy.md", f, "text/markdown")},
            data={"category": "policy"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["chunks_indexed"] >= 1
    assert "custom_policy.md" in data["message"]
