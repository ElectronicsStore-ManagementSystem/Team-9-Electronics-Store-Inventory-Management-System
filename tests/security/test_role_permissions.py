
import pytest


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    ("method", "endpoint", "payload"),
    [
        ("delete", "/api/inventory/1", None),
        ("post", "/api/inventory", {
            "name": "Permission Test Component",
            "category": "Testing",
            "quantity": 5,
            "unit_price": 10,
            "supplier": "Test Supplier",
        }),
        ("patch", "/api/inventory/1", {
            "name": "Unauthorized Update",
        }),
        ("get", "/api/audit-logs", None),
    ],
)
def test_staff_cannot_access_manager_only_endpoints(
    client, staff_token, method, endpoint, payload
):
    response = client.request(
        method,
        endpoint,
        headers=auth(staff_token),
        json=payload,
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    ("method", "endpoint"),
    [
        ("delete", "/api/inventory/1"),
        ("post", "/api/inventory"),
        ("patch", "/api/inventory/1"),
        ("get", "/api/audit-logs"),
    ],
)
def test_protected_endpoints_reject_unauthenticated_requests(
    client, method, endpoint
):
    response = client.request(method, endpoint)

    assert response.status_code == 401


def test_admin_can_access_audit_logs(client, admin_token):
    response = client.get(
        "/api/audit-logs",
        headers=auth(admin_token),
    )

    assert response.status_code == 200

