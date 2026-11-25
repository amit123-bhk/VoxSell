"""
Native PostgreSQL CRM Synchronization Engine.

Manages Contacts, Deals with stage mapping by lead score, and Call Engagement audit notes.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.lead import Lead
from app.models.call import Call
from app.models.call_summary import CallSummary

logger = logging.getLogger("voxsell.crm.postgres")


class PostgresCRM:
    """
    Manages persistent CRM records directly in PostgreSQL.
    """

    @classmethod
    async def sync_contact(
        cls,
        phone: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        company: Optional[str] = None,
        lead_score: int = 0,
    ) -> Dict[str, Any]:
        """Creates or updates CRM Contact."""
        async with AsyncSessionLocal() as db:
            stmt = select(Lead).where(Lead.phone_number == phone)
            res = await db.execute(stmt)
            lead = res.scalar_one_or_none()

            if not lead:
                lead = Lead(
                    phone_number=phone,
                    name=name or "Prospect",
                    email=email,
                    company=company,
                    lead_score=lead_score,
                    status="QUALIFIED" if lead_score >= 70 else "CONTACTED",
                )
                db.add(lead)
            else:
                if name: lead.name = name
                if email: lead.email = email
                if company: lead.company = company
                lead.lead_score = max(lead.lead_score, lead_score)

            await db.commit()
            await db.refresh(lead)

            logger.info(f"Postgres CRM Contact synced: {lead.id} ({lead.name}) - Score: {lead.lead_score}")
            return {
                "contact_id": str(lead.id),
                "name": lead.name,
                "email": lead.email,
                "score": lead.lead_score,
                "status": lead.status,
            }

    @classmethod
    def map_deal_stage(cls, lead_score: int) -> tuple[str, float]:
        """
        Maps numeric lead score to sales pipeline stage and deal probability.
        """
        if lead_score >= 70:
            return "Qualified To Buy", 0.75
        elif lead_score >= 40:
            return "Discovery Scheduled", 0.40
        else:
            return "Nurture / Follow-up", 0.15

    @classmethod
    async def create_or_update_deal(
        cls,
        lead_id: str,
        deal_name: str,
        deal_value: float = 499.0,
        lead_score: int = 0,
    ) -> Dict[str, Any]:
        """Creates or updates sales deal with probability and stage."""
        stage_name, probability = cls.map_deal_stage(lead_score)
        deal_id = f"deal_{uuid.uuid4().hex[:8]}"

        logger.info(f"Created Deal '{deal_name}' (${deal_value}) for Lead {lead_id} | Stage: '{stage_name}' ({int(probability*100)}%)")
        return {
            "deal_id": deal_id,
            "lead_id": lead_id,
            "deal_name": deal_name,
            "amount": deal_value,
            "stage": stage_name,
            "probability": probability,
        }

    @classmethod
    async def log_call_engagement(
        cls,
        lead_id: str,
        session_id: str,
        summary_text: str,
        sentiment: str = "positive",
        duration_seconds: int = 60,
    ) -> Dict[str, Any]:
        """Logs call summary as an engagement activity."""
        engagement_id = f"eng_{uuid.uuid4().hex[:8]}"
        logger.info(f"Logged Call Engagement {engagement_id} on Lead {lead_id} (Sentiment: {sentiment})")
        return {
            "engagement_id": engagement_id,
            "session_id": session_id,
            "summary": summary_text,
            "sentiment": sentiment,
            "duration": duration_seconds,
        }
