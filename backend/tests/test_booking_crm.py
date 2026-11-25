"""
Tests for Phase 7 Automated Booking & CRM Sync:
- Natural language datetime parsing (English & Hindi/Hinglish)
- Slot availability in Asia/Kolkata timezone
- Google Calendar booking & Meet link generation
- Booking idempotency (no duplicate slots for same lead)
- CRM deal stage mapping by lead score
- Async notification dispatch
"""

import pytest
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.calendar.natural_time import NaturalTimeParser, DEFAULT_TIMEZONE
from app.calendar.google_calendar import GoogleCalendarManager
from app.crm.postgres_crm import PostgresCRM
from app.crm.queue import NotificationService


def test_natural_time_parser_english():
    """Assert English natural expressions parse accurately to Asia/Kolkata timezone."""
    now = datetime(2026, 11, 25, 12, 0, tzinfo=DEFAULT_TIMEZONE)
    parsed = NaturalTimeParser.parse("tomorrow at 5pm", base_time=now)

    assert parsed is not None
    assert parsed.hour == 17
    assert parsed.minute == 0
    assert parsed.day == 26
    assert parsed.tzinfo == DEFAULT_TIMEZONE

    formatted = NaturalTimeParser.format_confirmation(parsed)
    assert "5:00 PM IST" in formatted


def test_natural_time_parser_hindi_hinglish():
    """Assert Hindi/Hinglish expressions like 'kal shaam 5 baje' parse correctly."""
    now = datetime(2026, 11, 25, 12, 0, tzinfo=DEFAULT_TIMEZONE)
    parsed = NaturalTimeParser.parse("kal shaam 5 baje", base_time=now)

    assert parsed is not None
    assert parsed.hour == 17
    assert parsed.day == 26

    formatted = NaturalTimeParser.format_confirmation(parsed)
    assert "5:00 PM IST" in formatted


@pytest.mark.asyncio
async def test_calendar_check_availability():
    """Assert calendar returns open business hour slots in Asia/Kolkata."""
    slots = await GoogleCalendarManager.check_availability("tomorrow")
    assert len(slots) > 0
    assert "05:00 PM" in slots or "11:00 AM" in slots


@pytest.mark.asyncio
async def test_calendar_book_and_idempotency():
    """Assert booking creates meeting and rejects duplicate booking for the same slot."""
    lead_id = str(uuid.uuid4())
    time_phrase = "tomorrow at 5pm"

    # 1. First Booking
    booking1 = await GoogleCalendarManager.book_appointment(
        lead_id=lead_id,
        natural_time=time_phrase,
        meeting_type="Enterprise Demo",
        attendee_email="aman@example.com",
    )
    assert booking1["status"] in {"confirmed", "already_booked"}
    assert "meet.google.com" in booking1["google_meet_link"]
    assert "5:00 PM IST" in booking1["formatted_time"]
    assert "Does that schedule work for you?" in booking1["spoken_confirmation"] or "already booked" in booking1["spoken_confirmation"]

    # 2. Second Booking Attempt (Idempotency)
    booking2 = await GoogleCalendarManager.book_appointment(
        lead_id=lead_id,
        natural_time=time_phrase,
        meeting_type="Enterprise Demo",
        attendee_email="aman@example.com",
    )
    assert booking2["status"] == "already_booked"
    assert "already booked" in booking2["spoken_confirmation"]


def test_crm_deal_stage_mapping_by_lead_score():
    """Assert lead scores map to appropriate sales pipeline stages."""
    # Hot Lead (>=70)
    stage_hot, prob_hot = PostgresCRM.map_deal_stage(85)
    assert stage_hot == "Qualified To Buy"
    assert prob_hot == 0.75

    # Warm Lead (40-69)
    stage_warm, prob_warm = PostgresCRM.map_deal_stage(55)
    assert stage_warm == "Discovery Scheduled"
    assert prob_warm == 0.40

    # Cold Lead (<40)
    stage_cold, prob_cold = PostgresCRM.map_deal_stage(25)
    assert stage_cold == "Nurture / Follow-up"
    assert prob_cold == 0.15


@pytest.mark.asyncio
async def test_notification_service_confirmation():
    """Assert meeting confirmation delivers via email and whatsapp."""
    res = await NotificationService.send_booking_confirmation(
        recipient_email="lead@example.com",
        recipient_phone="+919876543210",
        meeting_title="VoxSell Product Demo",
        formatted_time="Thursday, Nov 27 at 05:00 PM IST",
        google_meet_link="https://meet.google.com/vox-abc-defg",
    )
    assert res["status"] == "delivered"
    assert res["email_sent"] is True
    assert res["whatsapp_sent"] is True
