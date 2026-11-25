"""
Transcript database model storing per-turn dialogue, latency, and sentiment analysis.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Transcript(Base):
    """
    Fine-grained turn-by-turn dialogue store for each user and agent utterance.
    Essential for latency auditing, real-time sentiment tracking, and RAG context memory.
    """
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    speaker: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="'user' or 'agent'",
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    sentiment: Mapped[str] = mapped_column(String(32), default="neutral", nullable=False)
    sentiment_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Normalized score between -1.0 (very negative) and +1.0 (very positive)",
    )
    latency_ms: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Turn response latency in milliseconds from audio end to first TTS chunk",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    call: Mapped["Call"] = relationship("Call", back_populates="transcripts")

    def __repr__(self) -> str:
        return f"<Transcript(call={self.call_id}, turn={self.turn_number}, speaker={self.speaker}, latency={self.latency_ms}ms)>"
