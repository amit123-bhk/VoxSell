"""
Intelligent BANT Qualification and 0-100 Lead Scoring Engine.

Implements:
1. BANT evaluation (Budget 25, Authority 25, Need 25, Timeline 25).
2. Lead scoring calculation with sentiment and engagement modifiers.
3. Lead classification: Hot (>=70), Warm (40-69), Cold (<40).
4. Tool `update_qualification` and `escalate_to_human`.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.lead import Lead

logger = logging.getLogger("voxsell.agent.qualification")


class BANTScorer:
    """
    Computes a deterministic 0-100 Lead Score based on BANT completeness,
    sentiment polarity, and dialogue engagement depth.
    """

    @classmethod
    def calculate_score(
        cls,
        budget: Optional[str] = None,
        authority: Optional[str] = None,
        need: Optional[str] = None,
        timeline: Optional[str] = None,
        average_sentiment: float = 0.0,
        turn_count: int = 1,
    ) -> Dict[str, Any]:
        """
        Calculates score breakdown and classification.
        """
        budget_score = 0
        authority_score = 0
        need_score = 0
        timeline_score = 0

        # 1. Budget Score (0-25)
        if budget:
            b_lower = budget.lower()
            if any(k in b_lower for k in ["lakh", "crore", "$", "k", "month", "annual", "budget is"]):
                budget_score = 25
            else:
                budget_score = 15

        # 2. Authority Score (0-25)
        if authority:
            a_lower = authority.lower()
            if any(k in a_lower for k in ["founder", "ceo", "owner", "director", "vp", "head", "decision maker", "i decide"]):
                authority_score = 25
            elif any(k in a_lower for k in ["manager", "lead", "evaluating", "recommend"]):
                authority_score = 15
            else:
                authority_score = 8

        # 3. Need Score (0-25)
        if need:
            n_lower = need.lower()
            if any(k in n_lower for k in ["urgent", "losing leads", "scale", "automation", "replace", "inbound", "24/7"]):
                need_score = 25
            elif len(need) > 10:
                need_score = 18
            else:
                need_score = 10

        # 4. Timeline Score (0-25)
        if timeline:
            t_lower = timeline.lower()
            if any(k in t_lower for k in ["asap", "immediately", "this month", "this week", "urgent", "ready"]):
                timeline_score = 25
            elif any(k in t_lower for k in ["this quarter", "next month", "1-2 months", "soon"]):
                timeline_score = 18
            else:
                timeline_score = 10

        bant_subtotal = budget_score + authority_score + need_score + timeline_score

        # 5. Engagement & Sentiment Bonus (-10 to +10)
        sentiment_bonus = int(average_sentiment * 10)  # +9 to -9
        engagement_bonus = 5 if turn_count >= 3 else 0

        total_score = max(0, min(100, bant_subtotal + sentiment_bonus + engagement_bonus))

        # Classification
        if total_score >= 70:
            classification = "HOT"
        elif total_score >= 40:
            classification = "WARM"
        else:
            classification = "COLD"

        return {
            "total_score": total_score,
            "classification": classification,
            "breakdown": {
                "budget_points": budget_score,
                "authority_points": authority_score,
                "need_points": need_score,
                "timeline_points": timeline_score,
                "sentiment_modifier": sentiment_bonus,
                "engagement_bonus": engagement_bonus,
            }
        }


async def update_qualification(
    lead_id: str,
    budget: Optional[str] = None,
    authority: Optional[str] = None,
    need: Optional[str] = None,
    timeline: Optional[str] = None,
    notes: Optional[str] = None,
    average_sentiment: float = 0.0,
    turn_count: int = 1,
) -> Dict[str, Any]:
    """
    Tool function invoked by LLM or orchestrator to persist BANT attributes and update score.
    """
    logger.info(f"update_qualification invoked for lead {lead_id}: B={budget}, A={authority}, N={need}, T={timeline}")

    scoring = BANTScorer.calculate_score(
        budget=budget,
        authority=authority,
        need=need,
        timeline=timeline,
        average_sentiment=average_sentiment,
        turn_count=turn_count,
    )

    score = scoring["total_score"]
    status_label = "QUALIFIED" if score >= 70 else "WARM" if score >= 40 else "CONTACTED"

    try:
        async with AsyncSessionLocal() as db:
            lead_uuid = uuid.UUID(lead_id)
            stmt = select(Lead).where(Lead.id == lead_uuid)
            res = await db.execute(stmt)
            lead = res.scalar_one_or_none()

            if lead:
                if budget: lead.bant_budget = budget
                if authority: lead.bant_authority = authority
                if need: lead.bant_need = need
                if timeline: lead.bant_timeline = timeline
                lead.lead_score = score
                lead.status = status_label
                await db.commit()
                logger.info(f"Lead {lead_id} updated: Score={score} ({scoring['classification']})")
    except Exception as e:
        logger.debug(f"Ephemeral/offline DB update for qualification: {e}")

    return {
        "status": "success",
        "lead_id": lead_id,
        "lead_score": score,
        "classification": scoring["classification"],
        "breakdown": scoring["breakdown"],
    }


def escalate_to_human(
    reason: str,
    caller_phone: str,
    current_sentiment: str = "frustrated",
) -> Dict[str, Any]:
    """
    Escalates an angry or human-requesting caller to a human sales representative.
    """
    logger.warning(f"🚨 [HUMAN ESCALATION TRIGGERED] Phone: {caller_phone} | Reason: {reason} | Sentiment: {current_sentiment}")

    return {
        "status": "escalated",
        "action": "TRANSFER_TO_HUMAN_QUEUE",
        "caller_phone": caller_phone,
        "reason": reason,
        "sentiment": current_sentiment,
        "spoken_message": "I completely understand. I am transferring your call to a senior specialist right now. Please hold on for just a moment.",
    }


# Tool Definitions for LLM function calling
UPDATE_QUALIFICATION_TOOL = {
    "type": "function",
    "function": {
        "name": "update_qualification",
        "description": "Updates BANT qualification attributes (budget, authority, need, timeline) for the lead.",
        "parameters": {
            "type": "object",
            "properties": {
                "budget": {"type": "string", "description": "Known or stated budget range"},
                "authority": {"type": "string", "description": "Caller role or decision making capability"},
                "need": {"type": "string", "description": "Business pain points or requirements"},
                "timeline": {"type": "string", "description": "Purchasing timeframe (e.g. ASAP, 1 month, next quarter)"},
                "notes": {"type": "string", "description": "Additional context or objections"},
            },
        },
    },
}

ESCALATE_TO_HUMAN_TOOL = {
    "type": "function",
    "function": {
        "name": "escalate_to_human",
        "description": "Triggers immediate human agent transfer when the user explicitly asks for a human or is visibly angry.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Reason for escalation (e.g. 'Caller requested human', 'Angry customer')"},
            },
            "required": ["reason"],
        },
    },
}
