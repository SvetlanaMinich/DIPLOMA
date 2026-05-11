"""Audit log helper — write audit events without breaking main flow."""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditAction, AuditLog

logger = logging.getLogger(__name__)


async def write_audit_log(
    session: AsyncSession,
    *,
    user_id: UUID | None,
    action: AuditAction,
    log_msg: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Add an AuditLog entry to the current session (no separate commit)."""
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            log_msg=log_msg,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        session.add(entry)
    except Exception as exc:
        logger.warning("Audit log write failed (%s): %s", action, exc)
