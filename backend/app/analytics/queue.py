"""
Asynchronous Post-Call Job Queue.

Decouples post-call processing from the real-time voice loop:
1. Generates structured post-call summary JSON
2. Saves summary to database and syncs to CRM
3. Computes talk ratio, duration, latency, and RAG metrics
4. Records analytics and unanswered questions
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.call import Call
from app.analytics.summarizer import PostCallSummarizer
from app.analytics.metrics import CallMetricsCalculator, AnalyticsRepository

logger = logging.getLogger("voxsell.analytics.queue")


class PostCallQueue:
    """
    Manages non-blocking post-call analytics and summarization jobs.
    """

    @classmethod
    def enqueue(
        cls,
        call_id: str,
        transcripts: List[Dict[str, Any]],
        lead_id: Optional[str] = None,
        duration_seconds: int = 0,
        average_latency_ms: float = 0.0,
        booked_appointment: bool = False,
        appointment_time: Optional[str] = None,
        lead_score: int = 50,
    ) -> asyncio.Task:
        """
        Dispatches background task to process post-call pipeline without blocking WebSocket.
        """
        task = asyncio.create_task(
            cls._process_job(
                call_id=call_id,
                transcripts=transcripts,
                lead_id=lead_id,
                duration_seconds=duration_seconds,
                average_latency_ms=average_latency_ms,
                booked_appointment=booked_appointment,
                appointment_time=appointment_time,
                lead_score=lead_score,
            )
        )
        logger.info(f"Enqueued post-call processing job for call {call_id}")
        return task

    @classmethod
    async def _process_job(
        cls,
        call_id: str,
        transcripts: List[Dict[str, Any]],
        lead_id: Optional[str] = None,
        duration_seconds: int = 0,
        average_latency_ms: float = 0.0,
        booked_appointment: bool = False,
        appointment_time: Optional[str] = None,
        lead_score: int = 50,
    ) -> Dict[str, Any]:
        """Worker executing post-call summarization, metrics calculation, and CRM sync."""
        try:
            logger.info(f"Starting post-call job execution for call {call_id}...")

            # 1. Compute fine-grained metrics
            metrics = CallMetricsCalculator.compute_metrics(
                transcripts=transcripts,
                call_duration_seconds=duration_seconds,
                average_latency_ms=average_latency_ms,
            )

            # 2. Generate structured post-call summary JSON
            summary = await PostCallSummarizer.generate_summary(
                transcripts=transcripts,
                call_id=call_id,
                lead_id=lead_id,
                booked_appointment=booked_appointment,
                appointment_time=appointment_time,
                lead_score=lead_score,
            )

            # 3. Save to database and trigger CRM synchronization
            await PostCallSummarizer.save_and_sync(
                call_id=call_id,
                summary_data=summary,
                lead_id=lead_id,
            )

            # 4. Record to Analytics repository
            AnalyticsRepository.record_call(
                call_id=call_id,
                lead_score=summary["lead_score"],
                sentiment=summary["sentiment_overall"],
                duration=metrics["call_duration_seconds"],
                latency_ms=metrics["average_latency_ms"],
                booked=booked_appointment,
                talk_ratio=metrics["talk_ratio"],
                objections=summary["objections"],
                unanswered=metrics["unanswered_questions"],
            )

            # 5. Finalize Call record in database if UUID is valid
            try:
                call_uuid = uuid.UUID(call_id)
                async with AsyncSessionLocal() as db:
                    stmt = select(Call).where(Call.id == call_uuid)
                    res = await db.execute(stmt)
                    db_call = res.scalar_one_or_none()
                    if db_call:
                        db_call.status = "COMPLETED"
                        db_call.duration_seconds = metrics["call_duration_seconds"]
                        db_call.average_latency_ms = metrics["average_latency_ms"]
                        db_call.final_sentiment = summary["sentiment_overall"]
                        await db.commit()
            except Exception as e:
                logger.debug(f"Offline DB update for Call record {call_id}: {e}")

            logger.info(f"Post-call processing job finished successfully for call {call_id}")
            return {
                "call_id": call_id,
                "summary": summary,
                "metrics": metrics,
            }

        except Exception as e:
            logger.error(f"Error during post-call processing for call {call_id}: {e}", exc_info=True)
            return {"call_id": call_id, "error": str(e)}
