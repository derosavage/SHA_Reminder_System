"""
Audit Service
Immutable audit logging for compliance with Kenyan Data Protection Act 2019.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.audit import AuditLog, AuditAction


class AuditService:
    """Service for creating immutable audit log entries."""

    @staticmethod
    async def log(
        db: AsyncSession,
        action: AuditAction,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Create an immutable audit log entry.

        Args:
            db: Database session
            action: The audit action type
            user_id: ID of the user performing the action
            resource_type: Type of resource affected
            resource_id: ID of the resource affected
            description: Human-readable description
            metadata_json: Additional structured data
            ip_address: Client IP address
            user_agent: Client user agent string

        Returns:
            The created AuditLog entry
        """
        audit_entry = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            metadata_json=metadata_json or {},
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow(),
        )
        db.add(audit_entry)
        await db.commit()
        await db.refresh(audit_entry)

        logger.info(
            f"Audit: {action.value} | user={user_id} | "
            f"resource={resource_type}:{resource_id}"
        )
        return audit_entry

    @staticmethod
    async def get_user_audit_logs(
        db: AsyncSession,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Get audit logs for a specific user."""
        from sqlalchemy import select, desc

        count_query = select(AuditLog).where(AuditLog.user_id == user_id)
        total = len((await db.execute(count_query)).scalars().all())

        query = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.timestamp))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        logs = result.scalars().all()
        return list(logs), total

    @staticmethod
    async def get_recent_actions(
        db: AsyncSession,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get most recent audit actions across all users."""
        from sqlalchemy import select, desc

        query = (
            select(AuditLog)
            .order_by(desc(AuditLog.timestamp))
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())