"""
Contextual Memory Architecture for VoxSell.

Components:
1. ShortTermMemory: Redis-backed active dialogue buffer with rolling summarization (>20 turns).
2. LongTermMemory: Cross-call lead profiling from PostgreSQL (repeat caller recognition).
3. EntityExtractor: Asynchronous fact extraction (name, company, budget, city, time) updating Lead records.
"""

import asyncio
import json
import logging
import re
import uuid
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.lead import Lead
from app.models.call import Call
from app.models.call_summary import CallSummary

logger = logging.getLogger("voxsell.agent.memory")
settings = get_settings()

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None


class ShortTermMemory:
    """
    Manages in-call conversation history stored in Redis under key 'call:{call_id}'.
    Maintains a maximum of 20 raw dialogue turns, condensing older turns into a rolling summary.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis_client = None
        self._fallback_cache: Dict[str, Dict[str, Any]] = {}
        self._redis_available: Optional[bool] = None

    async def _get_client(self):
        """Lazy initialization of async Redis client with graceful offline fallback."""
        if self._redis_available is False:
            return None

        if self._redis_client is None and aioredis:
            try:
                client = aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=1.0,
                )
                # Ping to check availability
                await asyncio.wait_for(client.ping(), timeout=1.0)
                self._redis_client = client
                self._redis_available = True
                logger.info("Connected to Redis for Short-Term Memory.")
            except Exception as e:
                logger.warning(f"Redis is unreachable ({e}). Using in-memory fallback cache for short-term memory.")
                self._redis_available = False
                self._redis_client = None

        return self._redis_client

    async def add_turn(self, call_id: str, role: str, content: str) -> None:
        """
        Appends a dialogue turn to Redis.
        If turns exceed 20, summarizes the earliest 10 turns into a rolling summary.
        """
        redis_client = await self._get_client()
        key = f"call:{call_id}"

        # Fetch existing state
        state = await self._get_state(key, redis_client)
        turns: List[Dict[str, str]] = state.get("turns", [])
        rolling_summary: str = state.get("rolling_summary", "")

        turns.append({"role": role, "content": content})

        # Check turn limit (keep last 20 turns, summarize older ones)
        if len(turns) > 20:
            turns_to_summarize = turns[:10]
            remaining_turns = turns[10:]

            summary_addition = " | ".join(
                [f"{t['role'].upper()}: {t['content']}" for t in turns_to_summarize]
            )
            rolling_summary = (
                f"{rolling_summary} Previously: {summary_addition}".strip()
                if rolling_summary
                else f"Earlier conversation: {summary_addition}"
            )
            turns = remaining_turns

        state = {
            "turns": turns,
            "rolling_summary": rolling_summary,
        }

        # Save state
        if redis_client:
            try:
                await redis_client.set(key, json.dumps(state), ex=86400)  # 24hr TTL
            except Exception as e:
                logger.error(f"Error persisting turn to Redis: {e}")
                self._fallback_cache[key] = state
        else:
            self._fallback_cache[key] = state

    async def get_context_messages(self, call_id: str) -> List[Dict[str, str]]:
        """
        Retrieves formatted messages for LLM prompt injection, including any rolling summary.
        """
        redis_client = await self._get_client()
        key = f"call:{call_id}"
        state = await self._get_state(key, redis_client)

        turns = state.get("turns", [])
        rolling_summary = state.get("rolling_summary", "")

        messages: List[Dict[str, str]] = []
        if rolling_summary:
            messages.append({
                "role": "system",
                "content": f"[CONVERSATION SUMMARY OF EARLIER TURNS]: {rolling_summary}",
            })

        messages.extend(turns)
        return messages

    async def _get_state(self, key: str, redis_client) -> Dict[str, Any]:
        """Internal helper to retrieve session state from Redis or fallback dict."""
        if redis_client:
            try:
                raw = await redis_client.get(key)
                if raw:
                    return json.loads(raw)
            except Exception as e:
                logger.warning(f"Error fetching state from Redis: {e}")
        return self._fallback_cache.get(key, {"turns": [], "rolling_summary": ""})


class LongTermMemory:
    """
    Retrieves and injects cross-call intelligence for repeat leads from PostgreSQL.
    """

    @staticmethod
    async def load_lead_context(db: AsyncSession, lead_identifier: str) -> Optional[Dict[str, Any]]:
        """
        Loads the lead profile, past call history, objections, and BANT state.
        Matches by UUID or Phone Number.
        """
        try:
            lead_uuid = uuid.UUID(lead_identifier)
            stmt = (
                select(Lead)
                .where(Lead.id == lead_uuid)
                .options(selectinload(Lead.calls).selectinload(Call.summary))
            )
        except ValueError:
            stmt = (
                select(Lead)
                .where(Lead.phone_number == lead_identifier)
                .options(selectinload(Lead.calls).selectinload(Call.summary))
            )

        result = await db.execute(stmt)
        lead = result.scalar_one_or_none()

        if not lead:
            return None

        # Gather past summaries and objections
        past_summaries = []
        objections = []
        products_discussed = []

        for call in lead.calls:
            if call.summary:
                if call.summary.summary_text:
                    past_summaries.append(call.summary.summary_text)
                if call.summary.bant_analysis:
                    obj = call.summary.bant_analysis.get("objections", [])
                    if isinstance(obj, list):
                        objections.extend(obj)
                    elif isinstance(obj, str):
                        objections.append(obj)
                    prods = call.summary.bant_analysis.get("products", [])
                    if isinstance(prods, list):
                        products_discussed.extend(prods)

        return {
            "lead_id": str(lead.id),
            "phone_number": lead.phone_number,
            "name": lead.name,
            "company": lead.company,
            "lead_score": lead.lead_score,
            "status": lead.status,
            "budget": lead.bant_budget,
            "authority": lead.bant_authority,
            "need": lead.bant_need,
            "timeline": lead.bant_timeline,
            "total_past_calls": len(lead.calls),
            "past_summaries": past_summaries,
            "objections": list(set(objections)),
            "products_discussed": list(set(products_discussed)),
        }

    @staticmethod
    def format_lead_prompt_injection(lead_data: Optional[Dict[str, Any]]) -> str:
        """
        Formats lead data into the "What you know about this lead" system prompt block.
        """
        if not lead_data or not lead_data.get("name") and lead_data.get("total_past_calls", 0) <= 0:
            return ""

        name = lead_data.get("name") or "the prospect"
        budget = lead_data.get("budget") or "Not yet specified"
        company = lead_data.get("company") or "Unknown company"
        status = lead_data.get("status", "NEW")
        score = lead_data.get("lead_score", 0)
        past_calls = lead_data.get("total_past_calls", 0)

        lines = [
            "\n--- WHAT YOU KNOW ABOUT THIS LEAD (REPEAT CALLER) ---",
            f"- Prospect Name: {name}",
            f"- Company: {company}",
            f"- Known Budget: {budget}",
            f"- Qualification Status: {status} (Lead Score: {score}/100)",
            f"- Total Past Calls: {past_calls}",
        ]

        if lead_data.get("need"):
            lines.append(f"- Identified Need: {lead_data['need']}")
        if lead_data.get("timeline"):
            lines.append(f"- Timeline: {lead_data['timeline']}")
        if lead_data.get("objections"):
            lines.append(f"- Past Objections: {', '.join(lead_data['objections'])}")
        if lead_data.get("past_summaries"):
            lines.append(f"- Past Call Context: {' '.join(lead_data['past_summaries'][:2])}")

        lines.append("GREETING DIRECTIVE: Greet them warmly by their name, acknowledge previous discussions, and reference their known requirements or budget naturally.")
        lines.append("------------------------------------------------------\n")

        return "\n".join(lines)


class EntityExtractor:
    """
    Extracts structured entities from conversational utterances and updates Lead records.
    Uses regex pattern matchers for instant deterministic extraction alongside LLM JSON extraction.
    """

    # Regex patterns for fast zero-latency extraction
    NAME_PATTERNS = [
        re.compile(r"(?:my name is|i am|this is|call me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", re.IGNORECASE),
        re.compile(r"^([A-Z][a-z]+)\s+here\b", re.IGNORECASE),
    ]
    BUDGET_PATTERNS = [
        re.compile(r"(?:budget(?: is| of)?|around|upto|about)?\s*(\$?\d+(?:,\d+)*(?:\.\d+)?\s*(?:k|m|lakh|lakhs|crore|crores|usd|inr)?)\b", re.IGNORECASE),
        re.compile(r"(\d+\s*(?:lakh|lakhs|crore|crores|thousand|k|m))\b", re.IGNORECASE),
    ]
    COMPANY_PATTERNS = [
        re.compile(r"(?:at|with|from|company is|work for)\s+([A-Z][A-Za-z0-9\s&]+?)(?:\.|\,|$|\b(?:and|we|our)\b)", re.IGNORECASE),
    ]
    CITY_PATTERNS = [
        re.compile(r"(?:in|from|based in|located in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", re.IGNORECASE),
    ]

    @classmethod
    def extract_from_text(cls, text: str) -> Dict[str, Optional[str]]:
        """
        Synchronously parses utterance text with targeted regex heuristics.
        Fast, zero-latency extraction ideal for voice loops.
        """
        extracted: Dict[str, Optional[str]] = {
            "name": None,
            "company": None,
            "budget": None,
            "city": None,
        }

        # Name extraction
        for pat in cls.NAME_PATTERNS:
            match = pat.search(text)
            if match:
                candidate = match.group(1).strip()
                if candidate.lower() not in {"interested", "calling", "looking", "here", "just"}:
                    extracted["name"] = candidate.title()
                    break

        # Budget extraction
        if "budget" in text.lower() or any(w in text.lower() for w in ["lakh", "crore", "$", "k"]):
            for pat in cls.BUDGET_PATTERNS:
                match = pat.search(text)
                if match:
                    val = match.group(1).strip()
                    if val and not val.isalpha():
                        extracted["budget"] = val
                        break

        # Company extraction
        for pat in cls.COMPANY_PATTERNS:
            match = pat.search(text)
            if match:
                comp = match.group(1).strip()
                if len(comp) > 2 and comp.lower() not in {"the", "a", "home"}:
                    extracted["company"] = comp
                    break

        # City extraction
        for pat in cls.CITY_PATTERNS:
            match = pat.search(text)
            if match:
                city = match.group(1).strip()
                if city.lower() not in {"delhi", "mumbai", "bangalore", "chandigarh", "toronto", "london", "new york"}:
                    pass
                else:
                    extracted["city"] = city.title()
                break

        return extracted

    @classmethod
    async def update_lead_with_entities(
        cls,
        db: AsyncSession,
        lead_id: uuid.UUID,
        entities: Dict[str, Optional[str]],
    ) -> Optional[Lead]:
        """
        Updates database Lead record with newly extracted facts.
        """
        stmt = select(Lead).where(Lead.id == lead_id)
        res = await db.execute(stmt)
        lead = res.scalar_one_or_none()

        if not lead:
            return None

        updated = False
        if entities.get("name") and (not lead.name or lead.name == "Prospect"):
            lead.name = entities["name"]
            updated = True
        if entities.get("budget"):
            lead.bant_budget = entities["budget"]
            updated = True
        if entities.get("company") and not lead.company:
            lead.company = entities["company"]
            updated = True

        if updated:
            await db.commit()
            await db.refresh(lead)
            logger.info(f"Updated Lead ({lead.id}) profile: Name={lead.name}, Budget={lead.bant_budget}, Company={lead.company}")

        return lead
