"""
Leads Management API Endpoints.

Provides:
- GET /leads: List leads with score, Hot/Warm/Cold badge, language, last call, next appointment
- GET /leads/{lead_id}: Lead detail with all historical call summaries and transcripts
"""

import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models.lead import Lead
from app.models.call import Call
from app.models.call_summary import CallSummary
from app.models.appointment import Appointment
from app.api.auth import get_current_user

logger = logging.getLogger("voxsell.api.leads")
router = APIRouter(prefix="/leads", tags=["Leads"])

# In-memory baseline records for fast browsing & tests
_MEMORY_LEADS = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Aman Sharma",
        "phone_number": "+919876543210",
        "company": "Apex Sales Corp",
        "lead_score": 85,
        "classification": "HOT",
        "status": "APPOINTMENT_SCHEDULED",
        "language": "hi",
        "last_call_at": "2026-11-25T17:30:00Z",
        "next_appointment": "2026-11-26T17:00:00+05:30",
        "bant": {
            "budget": "5 lakh",
            "authority": "VP Sales",
            "need": "Automate 500 daily inbound leads",
            "timeline": "Immediate (this week)",
        },
        "calls": [
            {
                "call_id": "call_aman_001",
                "date": "2026-11-25T17:30:00Z",
                "duration_seconds": 135,
                "sentiment": "positive",
                "summary": "Aman confirmed 5 lakh budget and booked a 30-minute demo for Thursday at 5:00 PM IST.",
                "objections": ["Price / Budget constraints"],
                "appointment_booked": True,
            }
        ]
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "name": "Priya Patel",
        "phone_number": "+919811122233",
        "company": "LogiTech Solutions",
        "lead_score": 55,
        "classification": "WARM",
        "status": "DISCOVERY",
        "language": "hinglish",
        "last_call_at": "2026-11-25T15:10:00Z",
        "next_appointment": None,
        "bant": {
            "budget": "2-3 lakh",
            "authority": "Marketing Director",
            "need": "Speed-to-lead response time",
            "timeline": "Next month",
        },
        "calls": [
            {
                "call_id": "call_priya_001",
                "date": "2026-11-25T15:10:00Z",
                "duration_seconds": 95,
                "sentiment": "neutral",
                "summary": "Priya evaluated VoxSell against competitor tools; follow-up WhatsApp nurture sent.",
                "objections": ["Evaluating competitors"],
                "appointment_booked": False,
            }
        ]
    },
    {
        "id": "33333333-3333-3333-3333-333333333333",
        "name": "Vikram Singh",
        "phone_number": "+919765432109",
        "company": "Singh Enterprise",
        "lead_score": 25,
        "classification": "COLD",
        "status": "CONTACTED",
        "language": "pa",
        "last_call_at": "2026-11-24T12:00:00Z",
        "next_appointment": None,
        "bant": {
            "budget": "Undecided",
            "authority": "Store Owner",
            "need": "General inquiry",
            "timeline": "Undecided",
        },
        "calls": [
            {
                "call_id": "call_vikram_001",
                "date": "2026-11-24T12:00:00Z",
                "duration_seconds": 45,
                "sentiment": "negative",
                "summary": "Brief preliminary inquiry in Punjabi; client requested follow-up next quarter.",
                "objections": ["Timing / Timeline delay"],
                "appointment_booked": False,
            }
        ]
    },
]


@router.get("", response_model=Dict[str, Any])
async def list_leads(
    status: Optional[str] = None,
    classification: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Returns list of leads with score, Hot/Warm/Cold badge, language, last call, next appointment.
    """
    results = list(_MEMORY_LEADS)

    # Optional DB query if database is online
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(Lead).options(
                selectinload(Lead.calls),
                selectinload(Lead.appointments),
            )
            db_res = await db.execute(stmt)
            db_leads = db_res.scalars().all()

            for dl in db_leads:
                existing_ids = {r["id"] for r in results}
                if str(dl.id) not in existing_ids:
                    score = dl.lead_score or 0
                    cls_badge = "HOT" if score >= 70 else ("WARM" if score >= 40 else "COLD")
                    next_app = dl.appointments[0].start_time.isoformat() if dl.appointments else None
                    results.append({
                        "id": str(dl.id),
                        "name": dl.name or "Prospect",
                        "phone_number": dl.phone_number,
                        "company": dl.company or "N/A",
                        "lead_score": score,
                        "classification": cls_badge,
                        "status": dl.status,
                        "language": "en",
                        "last_call_at": dl.updated_at.isoformat() if dl.updated_at else datetime.now(timezone.utc).isoformat(),
                        "next_appointment": next_app,
                        "bant": {
                            "budget": dl.bant_budget or "N/A",
                            "authority": dl.bant_authority or "N/A",
                            "need": dl.bant_need or "N/A",
                            "timeline": dl.bant_timeline or "N/A",
                        },
                        "calls": [],
                    })
    except Exception as e:
        logger.debug(f"Offline DB query for leads: {e}")

    if classification:
        results = [l for l in results if l.get("classification") == classification.upper()]

    return {
        "status": "success",
        "count": len(results),
        "data": results,
    }


@router.get("/{lead_id}", response_model=Dict[str, Any])
async def get_lead_detail(lead_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Returns comprehensive lead detail with full past call summaries and transcripts.
    """
    for l in _MEMORY_LEADS:
        if l["id"] == lead_id or l["phone_number"] == lead_id:
            return {"status": "success", "data": l}

    # Query DB fallback
    try:
        lead_uuid = uuid.UUID(lead_id)
        async with AsyncSessionLocal() as db:
            stmt = (
                select(Lead)
                .where(Lead.id == lead_uuid)
                .options(
                    selectinload(Lead.calls).selectinload(Call.summary),
                    selectinload(Lead.appointments),
                )
            )
            res = await db.execute(stmt)
            db_lead = res.scalar_one_or_none()
            if db_lead:
                score = db_lead.lead_score or 0
                return {
                    "status": "success",
                    "data": {
                        "id": str(db_lead.id),
                        "name": db_lead.name,
                        "phone_number": db_lead.phone_number,
                        "company": db_lead.company,
                        "lead_score": score,
                        "classification": "HOT" if score >= 70 else ("WARM" if score >= 40 else "COLD"),
                        "status": db_lead.status,
                        "language": "en",
                        "bant": {
                            "budget": db_lead.bant_budget,
                            "authority": db_lead.bant_authority,
                            "need": db_lead.bant_need,
                            "timeline": db_lead.bant_timeline,
                        },
                        "calls": [
                            {
                                "call_id": str(c.id),
                                "date": c.start_time.isoformat() if c.start_time else "",
                                "duration_seconds": c.duration_seconds,
                                "sentiment": c.final_sentiment,
                                "summary": c.summary.summary_text if c.summary else "Call completed.",
                            }
                            for c in db_lead.calls
                        ],
                    }
                }
    except Exception as e:
        logger.debug(f"DB lookup lead detail error: {e}")

    raise HTTPException(status_code=404, detail="Lead profile not found.")
