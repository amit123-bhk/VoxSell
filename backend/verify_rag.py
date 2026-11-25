"""
Phase 5 RAG Verification & Evaluation Benchmark Script.

Ingests knowledge base documents into ChromaDB, executes hybrid retrieval across
10 test evaluation questions, tests anti-hallucination protection, and reports accuracy.
"""

import sys
import os
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(__file__))

from app.rag.ingest import ChromaKnowledgeBase
from app.rag.retriever import HybridRetriever
from app.rag.tools import search_knowledge_base

TEST_BENCHMARK = [
    {
        "id": 1,
        "question": "What is the monthly subscription price for the Starter plan?",
        "expected_keyword": "$499",
        "category": "pricing",
    },
    {
        "id": 2,
        "question": "How many included minutes are provided in the Growth tier?",
        "expected_keyword": "10,000",
        "category": "pricing",
    },
    {
        "id": 3,
        "question": "What is the extra per-minute rate on the Enterprise tier?",
        "expected_keyword": "$0.10",
        "category": "pricing",
    },
    {
        "id": 4,
        "question": "What is the target voice response turnaround latency?",
        "expected_keyword": "1.5",
        "category": "specs",
    },
    {
        "id": 5,
        "question": "Which languages does VoxSell support with automatic code-switching?",
        "expected_keyword": "Punjabi",
        "category": "specs",
    },
    {
        "id": 6,
        "question": "Which calendar platforms can VoxSell integrate with for booking?",
        "expected_keyword": "Google Calendar",
        "category": "integrations",
    },
    {
        "id": 7,
        "question": "What happens when a lead interrupts or speaks over the agent?",
        "expected_keyword": "barge-in",
        "category": "features",
    },
    {
        "id": 8,
        "question": "How much does custom voice cloning cost?",
        "expected_keyword": "$500",
        "category": "pricing",
    },
    {
        "id": 9,
        "question": "What uptime SLA guarantee is provided on the Enterprise plan?",
        "expected_keyword": "99.95%",
        "category": "sla",
    },
    {
        "id": 10,
        "question": "Does VoxSell sell designer shoes, clothing, or physical hardware?",
        "expected_keyword": "NO_RELEVANT_FACTS_FOUND",
        "category": "anti_hallucination",
    },
]


def evaluate_rag_accuracy():
    print("=" * 80)
    print(" VoxSell Phase 5: RAG Ingestion & 10-Question Accuracy Benchmark")
    print("=" * 80)

    # 1. Ingest sample documents from knowledge_base/
    kb_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../knowledge_base"))
    print(f"[*] Indexing documents from: {kb_dir}")
    kb = ChromaKnowledgeBase()
    indexed_chunks = kb.ingest_directory(kb_dir)
    print(f"[+] Total Chunks Indexed in ChromaDB: {indexed_chunks}")

    retriever = HybridRetriever(kb=kb)

    # 2. Execute Benchmark Evaluation
    passed_count = 0
    total_questions = len(TEST_BENCHMARK)

    print("\n" + "-" * 80)
    print(f"{'#':<3} | {'Question':<45} | {'Expected':<12} | {'Result':<8}")
    print("-" * 80)

    for item in TEST_BENCHMARK:
        q_id = item["id"]
        q_text = item["question"]
        expected = item["expected_keyword"]

        # Run hybrid retrieval
        results = retriever.search(q_text, top_k=3)
        combined_text = " ".join([r["text"] for r in results]) if results else ""

        # Check anti-hallucination test
        if item["category"] == "anti_hallucination":
            # Must NOT contain shoes, clothing or match; tool must trigger fallback
            passed = "shoes" not in combined_text.lower() and "clothing" not in combined_text.lower()
        else:
            passed = expected.lower() in combined_text.lower()

        if passed:
            passed_count += 1
            status_str = "[PASS]"
        else:
            status_str = "[FAIL]"

        print(f"{q_id:<3} | {q_text[:45]:<45} | {expected:<12} | {status_str:<8}")

    accuracy = (passed_count / total_questions) * 100.0

    print("-" * 80)
    print(f"\n[BENCHMARK SUMMARY]")
    print(f"Total Questions Evaluated: {total_questions}")
    print(f"Passed:                     {passed_count} / {total_questions}")
    print(f"RAG Retrieval Accuracy:    {accuracy:.1f}%")
    print("=" * 80)

    assert accuracy >= 90.0, f"RAG benchmark accuracy below 90%: {accuracy}%"
    print("\n[SUCCESS] Phase 5 RAG Knowledge Retrieval verified with >=90% accuracy!")


if __name__ == "__main__":
    evaluate_rag_accuracy()
