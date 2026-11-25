"""
Call database model representing an inbound or outbound audio session.
"""

from datetime import datetime
from typing import List, Optional
import uuid
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Call(Base, TimestampMixin):
    """
    Call session record tracking duration, latency metrics, and language detection.
    """
    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    session_id: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique identifier for WebSocket or Telephony session",
    )
    direction: Mapped[str] = mapped_column(String(16), default="INBOUND", nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default="INITIATED",
        nullable=False,
        comment="INITIATED, IN_PROGRESS, COMPLETED, FAILED",
    )
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    detected_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    average_latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    final_sentiment: Mapped[str] = mapped_column(String(32), default="neutral", nullable=False)

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="calls")
    transcripts: Mapped[List["Transcript"]] = relationship(
        "Transcript",
        back_populates="call",
        cascade="all, delete-orphan",
        order_by="Transcript.turn_number",
        lazy="selectin",
    )
    appointments: Mapped[List["Appointment"]] = relationship(
        "Appointment",
        back_populates="call",
    )
    summary: Mapped[Optional["CallSummary"]] = relationship(
        "CallSummary",
        back_populates="call",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Call(id={self.id}, session={self.session_id}, status={self.status}, lang={self.detected_language})>"
