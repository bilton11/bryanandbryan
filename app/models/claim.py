from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class ClaimStatus(str, enum.Enum):
    DRAFT = "draft"
    ASSESSED = "assessed"
    FILED = "filed"


# Dialect-adaptive JSON type: uses JSONB on PostgreSQL (native binary JSON with
# indexing support), falls back to JSON on SQLite (development). MutableDict
# wraps it so SQLAlchemy tracks in-place mutations (claim.step_data["key"] = …).
_JSONB_OR_JSON = MutableDict.as_mutable(JSONB().with_variant(JSON(), "sqlite"))


class Claim(db.Model):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus, name="claimstatus"),
        default=ClaimStatus.DRAFT,
        nullable=False,
    )
    current_step: Mapped[str] = mapped_column(
        String(50),
        default="dispute_type",
        nullable=False,
    )
    step_data: Mapped[Optional[dict]] = mapped_column(
        _JSONB_OR_JSON,
        nullable=True,
        default=dict,
    )
    ai_assessment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="claims")
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="claim"
    )

    __table_args__ = (
        Index("ix_claims_user_status", "user_id", "status"),
    )
