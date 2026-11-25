"""
Appointment database model for automated meeting scheduling and calendar sync.
"""

from datetime import datetime
from typing import Optional
import uuid
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Appointment(Base, TimestampMixin):
    """
    Appointment model storing scheduled sales meetings, Google Calendar sync IDs, and Meet links.
    """
    __tablename__ = "appointments"

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
    call_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    time_zone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)

    google_calendar_event_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    google_meet_link: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    attendee_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default="CONFIRMED",
        nullable=False,
        comment="CONFIRMED, CANCELLED, RESCHEDULED",
    )

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="appointments")
    call: Mapped[Optional["Call"]] = relationship("Call", back_populates="appointments")

    def __repr__(self) -> str:
        return f"<Appointment(id={self.id}, lead={self.lead_id}, start={self.start_time}, status={self.status})>"
