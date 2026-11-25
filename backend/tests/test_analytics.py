"""
Tests for Phase 8 Post-Call Processing & Analytics:
- Post-call structured summary generation conforming to exact JSON schema
- Talk ratio, duration, latency, and RAG metrics calculation
- Post-call asynchronous queue execution
- Endpoints: /analytics/overview, /analytics/trends, /analytics/top-objections, /analytics/unanswered-questions
- Weekly AI strategic business recommendations (5 insights)
"""

import pytest
import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.analytics.summarizer import PostCallSummarizer
from app.analytics.metrics import CallMetricsCalculator, AnalyticsRepository
from app.analytics.queue import PostCallQueue


@pytest.fixture
def test_transcripts():
    return [
        {"speaker": "agent", "text": "Hi there! I am Riya from VoxSell. Are you looking to automate your sales calls?", "latency_ms": 170.0},
        {"speaker": "user", "text": "Yes, we need to automate inbound qualification, but our budget is tight and your price seems expensive.", "latency_ms": 300.0},
        {"speaker": "agent", "text": "Our Growth Package at 499 dollars delivers a four-times ROI by saving 3200 dollars in team costs. Would tomorrow at 5pm work for a demo?", "latency_ms": 180.0},
        {"speaker": "user", "text": "That sounds great, let's book tomorrow at 5pm.", "latency_ms": 250.0},
        {"speaker": "agent", "text": "I have reserved our 30-minute demo for tomorrow at 5:00 PM IST. A Google Meet link has been sent.", "latency_ms": 165.0},
    ]


@pytest.mark.asyncio
async def test_post_call_summary_structured_schema(test_transcripts):
    """
    Asserts PostCallSummarizer generates exact required JSON schema:
    {summary, customer_needs, objections, products_discussed, next_steps, lead_score, sentiment_overall, appointment_booked, follow_up_date}
    """
    call_id = str(uuid.uuid4())
    summary = await PostCallSummarizer.generate_summary(
        transcripts=test_transcripts,
        call_id=call_id,
        booked_appointment=True,
        appointment_time="Thursday, Nov 26 at 05:00 PM IST",
        lead_score=85,
    )

    required_keys = {
        "summary",
        "customer_needs",
        "objections",
        "products_discussed",
        "next_steps",
        "lead_score",
        "sentiment_overall",
        "appointment_booked",
        "follow_up_date",
    }
    assert required_keys.issubset(summary.keys())
    assert summary["appointment_booked"] is True
    assert summary["lead_score"] == 85
    assert summary["sentiment_overall"] == "positive"
    assert "Price / Budget constraints" in summary["objections"]
    assert len(summary["customer_needs"]) > 0
    assert len(summary["products_discussed"]) > 0
    assert len(summary["next_steps"]) > 0


def test_call_metrics_calculator(test_transcripts):
    """
    Asserts CallMetricsCalculator computes talk ratio, latency, RAG questions answered, and unanswered questions.
    """
    metrics = CallMetricsCalculator.compute_metrics(
        transcripts=test_transcripts,
        call_duration_seconds=95,
        average_latency_ms=175.0,
    )

    assert "talk_ratio" in metrics
    ratio = metrics["talk_ratio"]
    assert 0.0 < ratio["agent_ratio"] < 1.0
    assert 0.0 < ratio["customer_ratio"] < 1.0
    assert round(ratio["agent_ratio"] + ratio["customer_ratio"], 1) == 1.0

    assert metrics["call_duration_seconds"] == 95
    assert metrics["average_latency_ms"] > 0
    assert metrics["rag_questions_answered"] >= 1  # Answered price & growth plan


def test_unanswered_question_detection():
    """
    Asserts anti-hallucination trigger ('let me confirm that and get back to you') logs the unanswered question.
    """
    transcripts_with_gap = [
        {"speaker": "user", "text": "Do you support on-premise air-gapped deployment?"},
        {"speaker": "agent", "text": "Let me confirm that and get back to you with our engineering specifications."},
    ]
    metrics = CallMetricsCalculator.compute_metrics(transcripts_with_gap)

    assert len(metrics["unanswered_questions"]) == 1
    assert "air-gapped" in metrics["unanswered_questions"][0]


@pytest.mark.asyncio
async def test_post_call_queue_end_to_end(test_transcripts):
    """
    Asserts PostCallQueue processes job, persists summary, and records analytics.
    """
    call_id = str(uuid.uuid4())
    lead_id = str(uuid.uuid4())

    res = await PostCallQueue._process_job(
        call_id=call_id,
        transcripts=test_transcripts,
        lead_id=lead_id,
        duration_seconds=110,
        average_latency_ms=172.0,
        booked_appointment=True,
        lead_score=80,
    )

    assert res["call_id"] == call_id
    assert res["summary"]["appointment_booked"] is True
    assert res["metrics"]["call_duration_seconds"] == 110


def test_analytics_api_endpoints():
    """
    Asserts FastAPI endpoints return proper HTTP 200 with structured response bodies.
    """
    client = TestClient(app)

    # 1. Overview
    res_overview = client.get("/analytics/overview")
    assert res_overview.status_code == 200
    data_overview = res_overview.json()["data"]
    assert data_overview["total_calls"] > 0
    assert "conversion_rate_percentage" in data_overview
    assert "lead_breakdown" in data_overview
    assert "hot" in data_overview["lead_breakdown"]

    # 2. Trends
    res_trends = client.get("/analytics/trends?days=7")
    assert res_trends.status_code == 200
    data_trends = res_trends.json()["data"]
    assert len(data_trends) == 7
    assert "appointments_booked" in data_trends[0]

    # 3. Top Objections
    res_objections = client.get("/analytics/top-objections")
    assert res_objections.status_code == 200
    data_objections = res_objections.json()["data"]
    assert len(data_objections) > 0
    assert "rebuttal_success_rate" in data_objections[0]

    # 4. Unanswered Questions
    res_unanswered = client.get("/analytics/unanswered-questions")
    assert res_unanswered.status_code == 200
    data_unanswered = res_unanswered.json()["data"]
    assert len(data_unanswered) > 0
    assert "frequency" in data_unanswered[0]

    # 5. Weekly Insights (5 Recommendations)
    res_insights = client.get("/analytics/insights")
    assert res_insights.status_code == 200
    data_insights = res_insights.json()["data"]
    assert len(data_insights["recommendations"]) == 5
    assert all("expected_impact" in rec for rec in data_insights["recommendations"])
