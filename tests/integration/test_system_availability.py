
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.db import SessionLocal
from app.models import AvailabilityCheck, DowntimeIncident, MaintenanceWindow


ENDPOINT = "/api/reports/system-availability"


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_system_availability_requires_authentication(client):
    response = client.get(
        ENDPOINT,
        params={"year": 2026, "month": 10},
    )

    assert response.status_code == 401


def test_system_availability_rejects_staff(client, staff_token):
    response = client.get(
        ENDPOINT,
        params={"year": 2026, "month": 10},
        headers=auth(staff_token),
    )

    assert response.status_code == 403


def test_system_availability_returns_no_data_message(client, admin_token):
    response = client.get(
        ENDPOINT,
        params={"year": 2026, "month": 10},
        headers=auth(admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["year"] == 2026
    assert data["month"] == 10
    assert data["monitoring_started"] is False
    assert data["availability_percentage"] is None
    assert data["target_met"] is None
    assert "No monitoring checks" in data["message"]


def test_system_availability_rejects_invalid_month(client, admin_token):
    response = client.get(
        ENDPOINT,
        params={"year": 2026, "month": 13},
        headers=auth(admin_token),
    )

    assert response.status_code == 422


def test_system_availability_rejects_invalid_year(client, admin_token):
    response = client.get(
        ENDPOINT,
        params={"year": 1999, "month": 10},
        headers=auth(admin_token),
    )

    assert response.status_code == 422


def test_system_availability_calculates_full_month_without_downtime(
    client, admin_token
):
    db = SessionLocal()

    try:
        month_start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        month_end = datetime(2025, 2, 1, tzinfo=timezone.utc)

        db.add_all([
            AvailabilityCheck(
                checked_at=month_start,
                is_available=True,
                response_time_ms=20,
            ),
            AvailabilityCheck(
                checked_at=month_end - timedelta(seconds=1),
                is_available=True,
                response_time_ms=22,
            ),
        ])
        db.commit()
    finally:
        db.close()

    response = client.get(
        ENDPOINT,
        params={"year": 2025, "month": 1},
        headers=auth(admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["monitoring_started"] is True
    assert data["coverage_complete"] is True
    assert data["availability_percentage"] == 100.0
    assert data["target_met"] is True


def test_system_availability_excludes_scheduled_maintenance(
    client, admin_token
):
    db = SessionLocal()

    try:
        month_start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        month_end = datetime(2025, 2, 1, tzinfo=timezone.utc)

        maintenance_start = datetime(2025, 1, 10, tzinfo=timezone.utc)
        maintenance_end = maintenance_start + timedelta(hours=2)

        db.add_all([
            AvailabilityCheck(
                checked_at=month_start,
                is_available=True,
            ),
            AvailabilityCheck(
                checked_at=month_end - timedelta(seconds=1),
                is_available=True,
            ),
            MaintenanceWindow(
                title="Scheduled maintenance",
                start_time=maintenance_start,
                end_time=maintenance_end,
            ),
            DowntimeIncident(
                started_at=maintenance_start,
                ended_at=maintenance_end,
                reason="Planned maintenance",
            ),
        ])
        db.commit()
    finally:
        db.close()

    response = client.get(
        ENDPOINT,
        params={"year": 2025, "month": 1},
        headers=auth(admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["coverage_complete"] is True
    assert data["availability_percentage"] == 100.0
    assert data["target_met"] is True


def test_system_availability_marks_incomplete_coverage(
    client, admin_token
):
    db = SessionLocal()

    try:
        # Checks cover only the first part of January.
        db.add_all([
            AvailabilityCheck(
                checked_at=datetime(
                    2025, 1, 1, tzinfo=timezone.utc
                ),
                is_available=True,
            ),
            AvailabilityCheck(
                checked_at=datetime(
                    2025, 1, 10, tzinfo=timezone.utc
                ),
                is_available=True,
            ),
        ])
        db.commit()
    finally:
        db.close()

    response = client.get(
        ENDPOINT,
        params={"year": 2025, "month": 1},
        headers=auth(admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["monitoring_started"] is True
    assert data["coverage_complete"] is False
    assert data["target_met"] is None
    assert "coverage is incomplete" in data["message"]




def test_system_availability_calculates_unplanned_downtime(
    client, admin_token
):
    db = SessionLocal()

    try:
        month_start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        month_end = datetime(2025, 2, 1, tzinfo=timezone.utc)

        downtime_start = datetime(2025, 1, 10, tzinfo=timezone.utc)
        downtime_end = downtime_start + timedelta(hours=5)

        db.add_all([
            AvailabilityCheck(
                checked_at=month_start,
                is_available=True,
            ),
            AvailabilityCheck(
                checked_at=month_end - timedelta(seconds=1),
                is_available=True,
            ),
            DowntimeIncident(
                started_at=downtime_start,
                ended_at=downtime_end,
                reason="Unexpected server outage",
            ),
        ])

        db.commit()
    finally:
        db.close()

    response = client.get(
        ENDPOINT,
        params={"year": 2025, "month": 1},
        headers=auth(admin_token),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["coverage_complete"] is True
    assert data["unplanned_downtime_seconds"] == 18000.0
    assert data["availability_percentage"] < 99.5
    assert data["target_met"] is False



def test_system_availability_handles_unexpected_reporting_error(
    client, admin_token
):
    with patch(
        "app.main.Session.query",
        side_effect=RuntimeError("Simulated database failure"),
    ):
        response = client.get(
            ENDPOINT,
            params={"year": 2025, "month": 1},
            headers=auth(admin_token),
        )

    assert response.status_code == 500