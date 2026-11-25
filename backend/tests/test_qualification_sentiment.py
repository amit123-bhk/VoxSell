"""
Tests for Phase 6 Intelligent Lead Qualification and Sentiment Analysis:
- Real-time sentiment & emotion classification
- Objection detection (Price, Timing, Competitor, Trust)
- BANT 0-100 scoring & classification (Hot, Warm, Cold)
- Human escalation triggers
"""

import pytest
from app.agent.sentiment import SentimentAnalyzer, ObjectionDetector
from app.agent.qualification import BANTScorer, escalate_to_human, update_qualification


def test_sentiment_analyzer_positive():
    """Assert positive sentiment and interested emotion are identified."""
    res = SentimentAnalyzer.analyze("This platform sounds really impressive and helpful!")
    assert res["sentiment"] == "positive"
    assert res["score"] > 0.3
    assert res["emotion"] == "interested"
    assert not res["requires_escalation"]


def test_sentiment_analyzer_frustrated():
    """Assert frustrated tone and negative polarity are detected."""
    res = SentimentAnalyzer.analyze("This is too expensive and completely useless for us.")
    assert res["sentiment"] == "negative"
    assert res["score"] < -0.4
    assert res["emotion"] == "frustrated"


def test_sentiment_analyzer_escalation_request():
    """Assert asking for a real person or human agent triggers escalation."""
    res = SentimentAnalyzer.analyze("I don't want to talk to an AI, transfer me to a real person!")
    assert res["requires_escalation"] is True


def test_objection_detector_price():
    """Assert price objections are identified with strategic rebuttal."""
    obj = ObjectionDetector.detect_objection("Your solution is too expensive for our current budget.")
    assert obj is not None
    assert obj["category"] == "price"
    assert "Starter tier" in obj["rebuttal_strategy"] or "ROI" in obj["rebuttal_strategy"]


def test_objection_detector_timing():
    """Assert timing objections are identified with strategic rebuttal."""
    obj = ObjectionDetector.detect_objection("We are too busy right now, call back next quarter.")
    assert obj is not None
    assert obj["category"] == "timing"


def test_bant_lead_scoring_hot():
    """Assert full BANT profile yields Hot classification (>=70)."""
    score_data = BANTScorer.calculate_score(
        budget="$1,499 per month",
        authority="I am the Founder and CEO",
        need="Need 24/7 automated inbound sales coverage",
        timeline="We are ready immediately this month",
        average_sentiment=0.6,
        turn_count=4,
    )
    assert score_data["total_score"] >= 70
    assert score_data["classification"] == "HOT"
    assert score_data["breakdown"]["budget_points"] == 25
    assert score_data["breakdown"]["authority_points"] == 25


def test_bant_lead_scoring_warm():
    """Assert partial BANT profile yields Warm classification (40-69)."""
    score_data = BANTScorer.calculate_score(
        budget="Maybe around 50k",
        authority="I am an evaluation manager",
        need=None,
        timeline="Next quarter",
        average_sentiment=0.0,
        turn_count=2,
    )
    assert 40 <= score_data["total_score"] < 70
    assert score_data["classification"] == "WARM"


def test_bant_lead_scoring_cold():
    """Assert unqualified inquiry yields Cold classification (<40)."""
    score_data = BANTScorer.calculate_score(
        budget=None,
        authority=None,
        need=None,
        timeline=None,
        average_sentiment=-0.3,
        turn_count=1,
    )
    assert score_data["total_score"] < 40
    assert score_data["classification"] == "COLD"


def test_escalate_to_human_tool():
    """Assert escalate_to_human produces structured handover action and spoken message."""
    handover = escalate_to_human(
        reason="Prospect requested manager",
        caller_phone="+19876543210",
        current_sentiment="frustrated",
    )
    assert handover["status"] == "escalated"
    assert handover["action"] == "TRANSFER_TO_HUMAN_QUEUE"
    assert "senior specialist" in handover["spoken_message"]
