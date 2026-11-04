from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient

from app.main import app


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def assert_error(response, code, status_code):
    assert response.status_code == status_code
    body = response.json()
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    assert "detail" in body


def test_missing_required_fields_use_standard_validation_error(client, admin_token):
    response = client.post(
        "/api/inventory",
        json={"name": "Incomplete component"},
        headers=auth(admin_token),
    )

    assert_error(response, "VALIDATION_ERROR", 422)
    assert response.json()["error"]["details"]
    assert any(
        detail["location"][-1] == "category"
        for detail in response.json()["error"]["details"]
    )


def test_invalid_inventory_data_uses_standard_validation_error(client, admin_token):
    response = client.post(
        "/api/inventory",
        json={
            "name": "Invalid component",
            "category": "Testing",
            "quantity": -1,
            "unit_price": 10,
            "supplier": "Test supplier",
        },
        headers=auth(admin_token),
    )

    assert_error(response, "VALIDATION_ERROR", 422)


def test_missing_component_uses_standard_not_found_error(client, admin_token):
    response = client.get(
        "/api/inventory/99999",
        headers=auth(admin_token),
    )

    assert_error(response, "NOT_FOUND", 404)


def test_unauthorized_and_forbidden_errors_use_standard_structure(
    client, staff_token
):
    unauthorized = client.get("/api/inventory")
    forbidden = client.get(
        "/api/reports/availability",
        headers=auth(staff_token),
    )

    assert_error(unauthorized, "UNAUTHORIZED", 401)
    assert unauthorized.headers["www-authenticate"] == "Bearer"
    assert_error(forbidden, "FORBIDDEN", 403)


def test_invalid_login_returns_safe_authentication_error(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "not-the-password"},
    )

    assert_error(response, "UNAUTHORIZED", 401)
    assert response.json()["error"]["message"] == "Invalid credentials"
    assert "password" not in response.text.lower()
    assert "hash" not in response.text.lower()


def test_super_admin_can_create_accounts_and_view_user_action_logs(client):
    login = client.post(
        "/api/auth/login",
        json={"username": "eims-admin", "password": "Password"},
    )
    assert login.status_code == 200
    headers = auth(login.json()["access_token"])

    created = client.post(
        "/api/users",
        json={
            "username": "viva-staff",
            "password": "VivaStaff1",
            "role": "STAFF",
        },
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["role"] == "STAFF"

    logs = client.get("/api/user-action-logs", headers=headers)
    assert logs.status_code == 200
    assert any(
        row["action"] == "CREATE_USER"
        and row["username"] == "eims-admin"
        for row in logs.json()
    )


def test_regular_admin_cannot_create_accounts_or_view_user_action_logs(
    client, admin_token
):
    headers = auth(admin_token)
    create_response = client.post(
        "/api/users",
        json={
            "username": "not-allowed",
            "password": "VivaStaff1",
            "role": "STAFF",
        },
        headers=headers,
    )
    logs_response = client.get("/api/user-action-logs", headers=headers)

    assert create_response.status_code == 403
    assert logs_response.status_code == 403


def test_duplicate_conflict_uses_standard_error(client, admin_token, monkeypatch):
    def raise_duplicate(*args, **kwargs):
        raise IntegrityError("duplicate SKU", {}, Exception("duplicate"))

    monkeypatch.setattr(
        "app.main.repositories.create_component",
        raise_duplicate,
    )

    response = client.post(
        "/api/inventory",
        json={
            "name": "Duplicate component",
            "category": "Testing",
            "quantity": 1,
            "unit_price": 10,
            "supplier": "Test supplier",
        },
        headers=auth(admin_token),
    )

    assert_error(response, "CONFLICT", 409)


def test_unexpected_errors_are_generic_and_standard(
    client, admin_token, monkeypatch
):
    def raise_unexpected(*args, **kwargs):
        raise RuntimeError("database password and stack trace")

    monkeypatch.setattr(
        "app.main.repositories.get_active_component",
        raise_unexpected,
    )

    response = TestClient(app, raise_server_exceptions=False).get(
        "/api/inventory/1",
        headers=auth(admin_token),
    )

    assert_error(response, "INTERNAL_SERVER_ERROR", 500)
    assert response.json()["error"]["message"] == (
        "An unexpected server error occurred. Please try again later."
    )
    assert "database password" not in response.text
    assert "RuntimeError" not in response.text


def test_inventory_and_reporting_validation_errors_share_structure(
    client, admin_token
):
    inventory = client.get(
        "/api/inventory?limit=not-a-number",
        headers=auth(admin_token),
    )
    report = client.get(
        "/api/reports/system-availability?year=not-a-year&month=13",
        headers=auth(admin_token),
    )

    assert_error(inventory, "VALIDATION_ERROR", 422)
    assert_error(report, "VALIDATION_ERROR", 422)
