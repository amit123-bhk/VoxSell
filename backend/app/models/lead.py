"""
Lead database model representing customer / prospect details and qualification status.
"""

from typing import List, Optional
import uuid
from sqlalchemy import String, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Lead(Base, TimestampMixin):
    """
    Lead model storing persistent prospect profile, multi-call BANT data, and scoring.
    """
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    phone_number: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
        comment="E.164 formatted phone number used as cross-call identifier",
    )
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Lead qualification and scoring
    lead_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default="NEW",
        nullable=False,
        comment="NEW, CONTACTED, QUALIFIED, DISQUALIFIED, APPOINTMENT_SCHEDULED",
    )
    preferred_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)

    # BANT Attributes
    bant_budget: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bant_authority: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bant_need: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bant_timeline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # External CRM reference
    crm_lead_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Relationships
    calls: Mapped[List["Call"]] = relationship(
        "Call",
        back_populates="lead",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    appointments: Mapped[List["Appointment"]] = relationship(
        "Appointment",
        back_populates="lead",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Lead(id={self.id}, phone={self.phone_number}, score={self.lead_score}, status={self.status})>"
