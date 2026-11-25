"""
LLM Tool Definition and Execution for RAG Knowledge Base Retrieval.

Exposes search_knowledge_base(query) to the agent so factual lookups are executed
strictly on-demand, preserving sub-second turnaround on conversational turns.
"""

import json
import logging
from typing import Dict, Any, List
from app.rag.retriever import HybridRetriever

logger = logging.getLogger("voxsell.rag.tools")

# Global singleton hybrid retriever
_retriever: HybridRetriever = None


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


def search_knowledge_base(query: str) -> str:
    """
    Searches the VoxSell product catalog, pricing plans, and FAQs using hybrid search.

    Args:
        query: Specific search question or keywords (e.g. "growth tier price", "calendar support").

    Returns:
        Formatted factual context string, or 'NO_RELEVANT_FACTS_FOUND'.
    """
    logger.info(f"RAG Tool Executing: search_knowledge_base('{query}')")
    retriever = get_retriever()
    results = retriever.search(query, top_k=3)

    if not results:
        return "NO_RELEVANT_FACTS_FOUND: The knowledge base has no documentation matching this question."

    formatted_facts = []
    for i, r in enumerate(results, 1):
        source = r.get("metadata", {}).get("source", "kb")
        text = r.get("text", "").strip()
        formatted_facts.append(f"[Fact {i} from {source}]:\n{text}")

    return "\n\n".join(formatted_facts)


# OpenAI Function / Tool Calling Schema
SEARCH_KB_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_knowledge_base",
        "description": "Searches the official VoxSell product catalog, pricing tiers, SLAs, and FAQs. Call this whenever the user asks about specific pricing, features, limits, integrations, or company policies.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query keywords or question to look up.",
                }
            },
            "required": ["query"],
        },
    },
}
