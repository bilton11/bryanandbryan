from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from flask_login import UserMixin
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    claims: Mapped[list["Claim"]] = relationship(
        "Claim", back_populates="user", lazy="dynamic"
    )
