
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AvailabilityCheck, DowntimeIncident


def record_availability_check(
    db: Session,
    is_available: bool,
    response_time_ms: float | None = None,
    error_message: str | None = None,
) -> AvailabilityCheck:
    """Record a check and update the current downtime incident."""

    checked_at = datetime.now(timezone.utc)

    check = AvailabilityCheck(
        checked_at=checked_at,
        is_available=is_available,
        response_time_ms=response_time_ms,
        error_message=error_message,
    )
    db.add(check)

    result = db.execute(
        select(DowntimeIncident)
        .where(DowntimeIncident.ended_at.is_(None))
        .order_by(DowntimeIncident.started_at.desc())
    )
    open_incident = result.scalars().first()

    if not is_available and open_incident is None:
        db.add(
            DowntimeIncident(
                started_at=checked_at,
                reason=error_message or "Application unavailable",
            )
        )

    elif is_available and open_incident is not None:
        open_incident.ended_at = checked_at

    db.commit()
    db.refresh(check)

    return check
