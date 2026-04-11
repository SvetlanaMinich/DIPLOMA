"""Template model for storing formatting templates."""
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID, uuid4

from app.core.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TemplateType(str, PyEnum):
    """Template type enumeration."""
    SYSTEM = "system"  # Default template managed by admin
    PERSONAL = "personal"  # User-created template


class Template(Base):
    """Template model for storing formatting templates."""

    __tablename__ = "templates"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,  # NULL for system templates
        index=True,
    )
    type: Mapped[TemplateType] = mapped_column(
        String(50),
        default=TemplateType.PERSONAL,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_json: Mapped[dict] = mapped_column(JSONB, nullable=False)  # Formatting rules
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Template(id={self.id}, name='{self.name}', type={self.type})>"
