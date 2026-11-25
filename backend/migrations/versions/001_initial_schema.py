"""Initial schema migration for Lead, Call, Transcript, Appointment, and CallSummary

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Leads Table
    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=False, comment="E.164 phone number"),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("lead_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="NEW"),
        sa.Column("preferred_language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("bant_budget", sa.Text(), nullable=True),
        sa.Column("bant_authority", sa.Text(), nullable=True),
        sa.Column("bant_need", sa.Text(), nullable=True),
        sa.Column("bant_timeline", sa.Text(), nullable=True),
        sa.Column("crm_lead_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_leads_id"), "leads", ["id"], unique=False)
    op.create_index(op.f("ix_leads_phone_number"), "leads", ["phone_number"], unique=True)
    op.create_index(op.f("ix_leads_email"), "leads", ["email"], unique=False)

    # 2. Calls Table
    op.create_table(
        "calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=False, comment="Unique session ID"),
        sa.Column("direction", sa.String(length=16), nullable=False, server_default="INBOUND"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="INITIATED"),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detected_language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("average_latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("final_sentiment", sa.String(length=32), nullable=False, server_default="neutral"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_calls_id"), "calls", ["id"], unique=False)
    op.create_index(op.f("ix_calls_lead_id"), "calls", ["lead_id"], unique=False)
    op.create_index(op.f("ix_calls_session_id"), "calls", ["session_id"], unique=True)

    # 3. Transcripts Table
    op.create_table(
        "transcripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("speaker", sa.String(length=16), nullable=False, comment="'user' or 'agent'"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("sentiment", sa.String(length=32), nullable=False, server_default="neutral"),
        sa.Column("sentiment_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_transcripts_id"), "transcripts", ["id"], unique=False)
    op.create_index(op.f("ix_transcripts_call_id"), "transcripts", ["call_id"], unique=False)
    op.create_index(op.f("ix_transcripts_turn_number"), "transcripts", ["turn_number"], unique=False)

    # 4. Appointments Table
    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("time_zone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("google_calendar_event_id", sa.String(length=255), nullable=True),
        sa.Column("google_meet_link", sa.String(length=512), nullable=True),
        sa.Column("attendee_email", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="CONFIRMED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_appointments_id"), "appointments", ["id"], unique=False)
    op.create_index(op.f("ix_appointments_lead_id"), "appointments", ["lead_id"], unique=False)
    op.create_index(op.f("ix_appointments_call_id"), "appointments", ["call_id"], unique=False)

    # 5. Call Summaries Table
    op.create_table(
        "call_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("key_points", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("bant_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("action_items", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("overall_sentiment", sa.String(length=32), nullable=False, server_default="neutral"),
        sa.Column("follow_up_needed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f("ix_call_summaries_id"), "call_summaries", ["id"], unique=False)
    op.create_index(op.f("ix_call_summaries_call_id"), "call_summaries", ["call_id"], unique=True)


def downgrade() -> None:
    op.drop_table("call_summaries")
    op.drop_table("appointments")
    op.drop_table("transcripts")
    op.drop_table("calls")
    op.drop_table("leads")
