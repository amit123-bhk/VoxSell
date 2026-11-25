"""
Business Intelligence and Analytics API Endpoints.

Provides:
- GET /analytics/overview: High-level KPI metrics (total calls, conversion rate, BANT breakdown, bookings)
- GET /analytics/trends: Daily historical volume and sentiment time series
- GET /analytics/top-objections: Ranked customer objections with frequency and rebuttal rates
- GET /analytics/unanswered-questions: Unanswered customer questions catalog for RAG curation
- GET /analytics/insights: Weekly 5 strategic AI business recommendations
- GET /analytics/calls: Paginated list of recent calls with summaries and metrics
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Query, HTTPException

from app.analytics.metrics import AnalyticsRepository
from app.analytics.summarizer import PostCallSummarizer

logger = logging.getLogger("voxsell.api.analytics")

router = APIRouter(prefix="/analytics", tags=["Analytics & Insights"])


@router.get("/overview", response_model=Dict[str, Any])
async def get_analytics_overview():
    """
    Returns executive KPI overview:
    Total calls, booking conversion rate, hot/warm/cold lead counts, avg sentiment, and latency.
    """
    try:
        data = await AnalyticsRepository.get_overview()
        return {
            "status": "success",
            "data": data,
        }
    except Exception as e:
        logger.error(f"Error fetching analytics overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends", response_model=Dict[str, Any])
async def get_analytics_trends(days: int = Query(default=7, ge=1, le=90)):
    """
    Returns daily time series for calls, appointments, and sentiment trends.
    """
    try:
        trends = await AnalyticsRepository.get_trends(days=days)
        return {
            "status": "success",
            "days": days,
            "data": trends,
        }
    except Exception as e:
        logger.error(f"Error fetching analytics trends: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-objections", response_model=Dict[str, Any])
async def get_top_objections():
    """
    Returns ranked customer objections, frequency counts, and rebuttal resolution rates.
    """
    try:
        objections = await AnalyticsRepository.get_top_objections()
        return {
            "status": "success",
            "total_objection_types": len(objections),
            "data": objections,
        }
    except Exception as e:
        logger.error(f"Error fetching top objections: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unanswered-questions", response_model=Dict[str, Any])
async def get_unanswered_questions():
    """
    Returns catalog of questions the AI agent could not answer with high confidence (RAG gaps).
    """
    try:
        questions = await AnalyticsRepository.get_unanswered_questions()
        return {
            "status": "success",
            "total_unanswered": len(questions),
            "data": questions,
        }
    except Exception as e:
        logger.error(f"Error fetching unanswered questions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights", response_model=Dict[str, Any])
async def get_weekly_insights():
    """
    Weekly AI executive insights: Reads aggregated call logs, conversion rates,
    and objections to write 5 data-driven business recommendations.
    """
    try:
        insights = await AnalyticsRepository.generate_weekly_insights()
        return {
            "status": "success",
            "data": insights,
        }
    except Exception as e:
        logger.error(f"Error generating weekly insights: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calls", response_model=Dict[str, Any])
async def get_recent_calls(limit: int = Query(default=20, ge=1, le=100)):
    """
    Returns recent call records with attached post-call structured summaries.
    """
    calls = list(reversed(AnalyticsRepository._in_memory_calls))[:limit]
    enhanced_calls = []

    for c in calls:
        cid = c.get("call_id", "")
        summary = PostCallSummarizer._in_memory_summaries.get(cid)
        record = dict(c)
        if summary:
            record["summary"] = summary
        enhanced_calls.append(record)

    return {
        "status": "success",
        "count": len(enhanced_calls),
        "data": enhanced_calls,
    }
