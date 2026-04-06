from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class DocumentType(str, enum.Enum):
    DEMAND_LETTER = "demand_letter"
    FORM_7A = "form_7a"
    FORM_9A = "form_9a"


# Dialect-adaptive JSON type: uses JSONB on PostgreSQL (native binary JSON with
# indexing support), falls back to JSON on SQLite (development). MutableDict
# wraps it so SQLAlchemy tracks in-place mutations.
_JSONB_OR_JSON = MutableDict.as_mutable(JSONB().with_variant(JSON(), "sqlite"))


class Document(db.Model):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("claims.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    doc_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="documenttype"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="",
    )
    input_data: Mapped[Optional[dict]] = mapped_column(
        _JSONB_OR_JSON,
        nullable=True,
        default=dict,
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
    user: Mapped["User"] = relationship("User", back_populates="documents")
    claim: Mapped[Optional["Claim"]] = relationship("Claim", back_populates="documents")
    versions: Mapped[list["DocumentVersion"]] = relationship(
        "DocumentVersion",
        back_populates="document",
        order_by="DocumentVersion.version_number.desc()",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_documents_user_doc_type", "user_id", "doc_type"),
    )

    def latest_version_number(self) -> int:
        """Return the highest version_number among versions, or 0 if none."""
        if not self.versions:
            return 0
        return max(v.version_number for v in self.versions)


class DocumentVersion(db.Model):
    __tablename__ = "document_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(nullable=False, default=1)
    input_data_snapshot: Mapped[Optional[dict]] = mapped_column(
        _JSONB_OR_JSON,
        nullable=True,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_version"),
    )
