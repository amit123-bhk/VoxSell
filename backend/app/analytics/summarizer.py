"""
Post-Call Summarization Engine.

Extracts structured conversation insights upon call completion:
- Executive summary narrative
- Customer needs and pain points
- Objections raised
- Products discussed
- Action items & next steps
- Final BANT lead score
- Overall sentiment
- Appointment booking status and follow-up date
- Syncs to CallSummary database model and external CRM
"""

import logging
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select

from app.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.call_summary import CallSummary
from app.models.call import Call
from app.crm.postgres_crm import PostgresCRM
from app.crm.hubspot import HubSpotCRMAdapter

logger = logging.getLogger("voxsell.analytics.summarizer")
settings = get_settings()


class PostCallSummarizer:
    """
    Transforms turn-by-turn dialogue into a structured post-call intelligence JSON.
    """

    _in_memory_summaries: Dict[str, Dict[str, Any]] = {}

    @classmethod
    async def generate_summary(
        cls,
        transcripts: List[Dict[str, Any]],
        call_id: Optional[str] = None,
        lead_id: Optional[str] = None,
        booked_appointment: bool = False,
        appointment_time: Optional[str] = None,
        lead_score: int = 50,
    ) -> Dict[str, Any]:
        """
        Generates structured post-call JSON summary conforming to:
        {summary, customer_needs, objections, products_discussed, next_steps, lead_score, sentiment_overall, appointment_booked, follow_up_date}
        """
        # Aggregate full conversation
        dialogue_lines = []
        user_utterances = []
        for t in transcripts:
            speaker = t.get("speaker", "user").capitalize()
            text = t.get("text", "").strip()
            if text:
                dialogue_lines.append(f"{speaker}: {text}")
                if speaker.lower() == "user":
                    user_utterances.append(text)

        full_dialogue = "\n".join(dialogue_lines)
        user_combined = " ".join(user_utterances).lower()

        # 1. Objections extraction
        objections = []
        if any(w in user_combined for w in ["expensive", "cost", "budget", "price", "discount", "pricey"]):
            objections.append("Price / Budget constraints")
        if any(w in user_combined for w in ["later", "next quarter", "busy", "timing", "not now"]):
            objections.append("Timing / Timeline delay")
        if any(w in user_combined for w in ["competitor", "other tool", "evaluating", "alternative"]):
            objections.append("Evaluating competitors")
        if any(w in user_combined for w in ["security", "trust", "privacy", "soc2", "gdpr", "data"]):
            objections.append("Data privacy & enterprise compliance")

        # 2. Products discussed
        products = []
        if any(w in user_combined for w in ["starter", "basic", "trial"]):
            products.append("VoxSell Starter Plan ($199/mo)")
        if any(w in user_combined for w in ["growth", "scale", "medium"]):
            products.append("VoxSell Growth Package ($499/mo)")
        if any(w in user_combined for w in ["enterprise", "custom", "high volume", "sla"]):
            products.append("VoxSell Enterprise Plan ($999+/mo)")
        if not products:
            products.append("VoxSell AI Voice Agent Platform")

        # 3. Customer needs
        needs = []
        if any(w in user_combined for w in ["automate", "automation", "scale"]):
            needs.append("Automate inbound sales qualification calls")
        if any(w in user_combined for w in ["lead", "conversion", "rate", "pipeline"]):
            needs.append("Increase lead conversion rate and speed-to-lead")
        if any(w in user_combined for w in ["hindi", "multilingual", "punjabi", "hinglish", "language"]):
            needs.append("Multilingual sales coverage for regional prospects")
        if any(w in user_combined for w in ["crm", "hubspot", "calendar", "booking"]):
            needs.append("Zero-friction CRM sync and automated demo scheduling")
        if not needs:
            needs.append("Explore AI voice sales agent capabilities")

        # 4. Sentiment overall
        positive_keywords = ["great", "awesome", "perfect", "good", "yes", "definitely", "interested", "sahi", "badhiya", "theek"]
        negative_keywords = ["bad", "frustrated", "angry", "no", "expensive", "stop", "waste", "slow", "bekaar"]

        pos_count = sum(user_combined.count(w) for w in positive_keywords)
        neg_count = sum(user_combined.count(w) for w in negative_keywords)

        if booked_appointment or pos_count > neg_count:
            sentiment_overall = "positive"
        elif neg_count > pos_count:
            sentiment_overall = "negative"
        else:
            sentiment_overall = "neutral"

        # 5. Next steps & Follow-up date
        next_steps = []
        follow_up_date = None

        if booked_appointment:
            next_steps.append(f"Attend scheduled product demo on {appointment_time or 'confirmed calendar slot'}")
            next_steps.append("Send calendar invite and pre-meeting collateral via email")
            follow_up_date = appointment_time or datetime.now(timezone.utc).isoformat()
        else:
            next_steps.append("Follow up with pricing brochure and case studies within 48 hours")
            next_steps.append("Nurture prospect via WhatsApp / Email drip sequence")
            follow_up_date = "48 hours"

        # 6. Concise Narrative Summary
        summary = (
            f"Prospect engaged in a sales discovery call discussing {', '.join(products[:2])}. "
            f"Key focus was on {needs[0].lower()}. "
            f"Objections raised: {', '.join(objections) if objections else 'None'}. "
            f"Outcome: {'Demo scheduled successfully' if booked_appointment else 'Nurture sequence recommended'}."
        )

        structured_result = {
            "summary": summary,
            "customer_needs": needs,
            "objections": objections,
            "products_discussed": products,
            "next_steps": next_steps,
            "lead_score": max(lead_score, 75 if booked_appointment else lead_score),
            "sentiment_overall": sentiment_overall,
            "appointment_booked": booked_appointment,
            "follow_up_date": follow_up_date,
        }

        # Cache in memory
        cid = call_id or str(uuid.uuid4())
        cls._in_memory_summaries[cid] = structured_result

        return structured_result

    @classmethod
    async def save_and_sync(
        cls,
        call_id: str,
        summary_data: Dict[str, Any],
        lead_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Persists summary to CallSummary model and triggers CRM synchronization.
        """
        # 1. Update in-memory store
        cls._in_memory_summaries[call_id] = summary_data

        # 2. Database Persistence (Non-blocking fallback)
        try:
            call_uuid = uuid.UUID(call_id)
            async with AsyncSessionLocal() as db:
                # Check existing summary
                stmt = select(CallSummary).where(CallSummary.call_id == call_uuid)
                res = await db.execute(stmt)
                existing = res.scalar_one_or_none()

                if existing:
                    existing.summary_text = summary_data["summary"]
                    existing.key_points = summary_data["customer_needs"]
                    existing.bant_analysis = summary_data
                    existing.action_items = summary_data["next_steps"]
                    existing.overall_sentiment = summary_data["sentiment_overall"]
                    existing.follow_up_needed = not summary_data["appointment_booked"]
                else:
                    new_summary = CallSummary(
                        call_id=call_uuid,
                        summary_text=summary_data["summary"],
                        key_points=summary_data["customer_needs"],
                        bant_analysis=summary_data,
                        action_items=summary_data["next_steps"],
                        overall_sentiment=summary_data["sentiment_overall"],
                        follow_up_needed=not summary_data["appointment_booked"],
                    )
                    db.add(new_summary)

                # Update call final sentiment
                call_stmt = select(Call).where(Call.id == call_uuid)
                call_res = await db.execute(call_stmt)
                db_call = call_res.scalar_one_or_none()
                if db_call:
                    db_call.final_sentiment = summary_data["sentiment_overall"]

                await db.commit()
                logger.info(f"PostCallSummary saved to DB for call {call_id}")
        except Exception as e:
            logger.debug(f"Offline DB save for CallSummary: {e}")

        # 3. CRM Sync
        crm_note_text = (
            f"=== VOXSELL AI CALL SUMMARY ===\n"
            f"Summary: {summary_data['summary']}\n"
            f"Lead Score: {summary_data['lead_score']}/100\n"
            f"Sentiment: {summary_data['sentiment_overall'].upper()}\n"
            f"Appointment Booked: {summary_data['appointment_booked']}\n"
            f"Customer Needs: {', '.join(summary_data['customer_needs'])}\n"
            f"Objections: {', '.join(summary_data['objections']) if summary_data['objections'] else 'None'}\n"
            f"Next Steps: {', '.join(summary_data['next_steps'])}\n"
        )

        try:
            if lead_id:
                # Sync engagement note to Postgres CRM
                await PostgresCRM.log_call_engagement(
                    lead_id=lead_id,
                    session_id=call_id,
                    summary_text=crm_note_text,
                    sentiment=summary_data["sentiment_overall"],
                )
                logger.info(f"Synced post-call summary to Postgres CRM for lead {lead_id}")
        except Exception as e:
            logger.warning(f"Error syncing summary to CRM: {e}")

        return summary_data
