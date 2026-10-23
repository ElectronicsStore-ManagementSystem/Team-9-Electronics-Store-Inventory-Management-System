from datetime import datetime

import pytest


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_unauthenticated_inventory_is_rejected(client):
    r = client.get("/api/inventory")
    assert r.status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        "/api/me",
        "/api/inventory",
        "/api/inventory/1",
        "/api/reports/availability",
        "/api/dashboard",
        "/api/audit-logs",
    ],
)
def test_all_protected_read_routes_require_authentication(client, path):
    response = client.get(path)

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "path",
    [
        "/api/me",
        "/api/inventory",
        "/api/inventory/1",
        "/api/reports/availability",
        "/api/dashboard",
        "/api/audit-logs",
    ],
)
def test_all_protected_read_routes_reject_invalid_tokens(client, path):
    response = client.get(
        path,
        headers={"Authorization": "Bearer not-a-valid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"
    assert response.headers["www-authenticate"] == "Bearer"


def test_seeded_user_passwords_are_salted_hashes_and_plaintext_is_rejected(
    client,
):
    from app.db import SessionLocal
    from app.models import User
    from app.security import verify_password

    db = SessionLocal()
    try:
        admin = db.query(User).filter_by(username="admin").one()
        staff = db.query(User).filter_by(username="staff").one()
        admin_hash = admin.password_hash
        staff_hash = staff.password_hash
        assert admin_hash != "Admin@12345"
        assert staff_hash != "Staff@12345"
        assert admin_hash.split("$")[2] != staff_hash.split("$")[2]
        assert verify_password("Admin@12345", admin_hash)
        assert verify_password("Staff@12345", staff_hash)
    finally:
        db.close()

    admin_login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "Admin@12345"},
    )
    assert admin_login.status_code == 200
    assert "password_hash" not in admin_login.json()

    db = SessionLocal()
    try:
        admin = db.query(User).filter_by(username="admin").one()
        admin.password_hash = "Admin@12345"
        db.commit()
    finally:
        db.close()

    plaintext_login = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "Admin@12345"},
    )
    assert plaintext_login.status_code == 401


def test_staff_can_read_inventory(client, staff_token):
    r = client.get(
        "/api/inventory",
        headers=auth(staff_token),
    )
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_component_details_are_available_to_authenticated_users(
    client, admin_token, staff_token
):
    admin_headers = auth(admin_token)
    created = client.post(
        "/api/inventory",
        json={
            "name": "Detail Test Component",
            "category": "Test",
            "quantity": 7,
            "unit_price": 12.5,
            "supplier": "Test Supplier",
            "reorder_level": 2,
        },
        headers=admin_headers,
    )
    assert created.status_code == 201
    component_id = created.json()["id"]

    assert client.get(f"/api/inventory/{component_id}").status_code == 401

    admin_response = client.get(
        f"/api/inventory/{component_id}",
        headers=admin_headers,
    )
    staff_response = client.get(
        f"/api/inventory/{component_id}",
        headers=auth(staff_token),
    )

    assert admin_response.status_code == 200
    assert staff_response.status_code == 200
    assert admin_response.json()["name"] == "Detail Test Component"
    assert admin_response.json()["created_at"] == created.json()["created_at"]
    assert staff_response.json()["created_at"] is None

    staff_inventory = client.get(
        "/api/inventory",
        headers=auth(staff_token),
    )
    assert staff_inventory.status_code == 200
    assert all(item["created_at"] is None for item in staff_inventory.json())

    staff_dashboard = client.get(
        "/api/dashboard",
        headers=auth(staff_token),
    )
    assert staff_dashboard.status_code == 200
    assert all(
        item["created_at"] is None
        for item in staff_dashboard.json()["recently_added"]
    )

    staff_availability = client.get(
        "/api/reports/availability",
        headers=auth(staff_token),
    )
    assert staff_availability.status_code == 200
    assert all(
        item["created_at"] is None
        for item in staff_availability.json()
    )

    assert client.get(
        "/api/inventory?sort=date_added",
        headers=auth(staff_token),
    ).status_code == 422

    deleted = client.delete(
        f"/api/inventory/{component_id}",
        headers=admin_headers,
    )
    assert deleted.status_code == 200
    assert client.get(
        f"/api/inventory/{component_id}",
        headers=admin_headers,
    ).status_code == 404


def test_staff_cannot_add_or_delete(client, staff_token):
    h = auth(staff_token)

    payload = {
        "name": "Test MCU",
        "category": "Microcontroller",
        "quantity": 3,
        "unit_price": 100,
        "supplier": "Test Supplier",
        "reorder_level": 2,
    }

    assert client.post(
        "/api/inventory",
        json=payload,
        headers=h,
    ).status_code == 403
    assert len(client.get("/api/inventory", headers=h).json()) == 3

    assert client.delete(
        "/api/inventory/1",
        headers=h,
    ).status_code == 403


def test_staff_cannot_update_components(client, staff_token):
    response = client.patch(
        "/api/inventory/1",
        json={"quantity": 1},
        headers=auth(staff_token),
    )

    assert response.status_code == 403


def test_manager_can_add_component_and_find_it_afterward(client):
    from app.db import SessionLocal
    from app.models import User
    from app.security import hash_password

    db = SessionLocal()
    try:
        db.add(
            User(
                username="adding_manager",
                password_hash=hash_password("Manager@12345"),
                role="MANAGER",
            )
        )
        db.commit()
    finally:
        db.close()

    login = client.post(
        "/api/auth/login",
        json={"username": "adding_manager", "password": "Manager@12345"},
    )
    assert login.status_code == 200
    headers = auth(login.json()["access_token"])
    payload = {
        "name": "New Stock Component",
        "category": "Connectors",
        "quantity": 24,
        "unit_price": 3.75,
        "supplier": "Parts Warehouse",
    }

    created = client.post("/api/inventory", json=payload, headers=headers)
    assert created.status_code == 201
    item = created.json()
    assert item["sku"].startswith("EIMS-")
    assert item["id"] is not None
    assert item["reorder_level"] == 5

    listed = client.get("/api/inventory", headers=headers)
    assert listed.status_code == 200
    assert any(
        component["id"] == item["id"]
        and component["name"] == payload["name"]
        and component["category"] == payload["category"]
        and component["quantity"] == payload["quantity"]
        and component["unit_price"] == payload["unit_price"]
        and component["supplier"] == payload["supplier"]
        for component in listed.json()
    )

    reopened = client.get(
        f"/api/inventory/{item['id']}",
        headers=headers,
    )
    assert reopened.status_code == 200
    assert reopened.json()["sku"] == item["sku"]


@pytest.mark.parametrize(
    "missing_field",
    ["name", "category", "quantity", "unit_price", "supplier"],
)
def test_add_component_requires_all_mandatory_fields(
    client, admin_token, missing_field
):
    payload = {
        "name": "Validation Component",
        "category": "Validation",
        "quantity": 5,
        "unit_price": 2.5,
        "supplier": "Validation Supplier",
    }
    del payload[missing_field]

    response = client.post(
        "/api/inventory",
        json=payload,
        headers=auth(admin_token),
    )

    assert response.status_code == 422
    assert len(client.get(
        "/api/inventory",
        headers=auth(admin_token),
    ).json()) == 3


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", "   "),
        ("category", "   "),
        ("supplier", "   "),
        ("quantity", -1),
        ("unit_price", -0.01),
        ("unit_price", "NaN"),
        ("reorder_level", -1),
    ],
)
def test_add_component_rejects_invalid_values(
    client, admin_token, field, value
):
    payload = {
        "name": "Validation Component",
        "category": "Validation",
        "quantity": 5,
        "unit_price": 2.5,
        "supplier": "Validation Supplier",
    }
    payload[field] = value

    response = client.post(
        "/api/inventory",
        json=payload,
        headers=auth(admin_token),
    )

    assert response.status_code == 422
    assert len(client.get(
        "/api/inventory",
        headers=auth(admin_token),
    ).json()) == 3


def test_authorized_manager_can_update_all_editable_component_fields(
    client, admin_token
):
    from app.db import SessionLocal
    from app.models import User
    from app.security import hash_password

    headers = auth(admin_token)
    created = client.post(
        "/api/inventory",
        json={
            "name": "Editable Component",
            "category": "Test",
            "quantity": 3,
            "unit_price": 8.5,
            "supplier": "Old Supplier",
            "reorder_level": 1,
        },
        headers=headers,
    )
    assert created.status_code == 201
    component_id = created.json()["id"]

    db = SessionLocal()
    try:
        db.add(
            User(
                username="inventory_manager",
                password_hash=hash_password("Manager@12345"),
                role="MANAGER",
            )
        )
        db.commit()
    finally:
        db.close()

    manager_login = client.post(
        "/api/auth/login",
        json={"username": "inventory_manager", "password": "Manager@12345"},
    )
    assert manager_login.status_code == 200
    manager_headers = auth(manager_login.json()["access_token"])

    updated = client.patch(
        f"/api/inventory/{component_id}",
        json={
            "quantity": 12,
            "unit_price": 14.75,
            "supplier": "  New Supplier  ",
            "reorder_level": 4,
        },
        headers=manager_headers,
    )

    assert updated.status_code == 200
    assert {
        key: updated.json()[key]
        for key in ("quantity", "unit_price", "supplier", "reorder_level")
    } == {
        "quantity": 12,
        "unit_price": 14.75,
        "supplier": "New Supplier",
        "reorder_level": 4,
    }

    reopened = client.get(
        f"/api/inventory/{component_id}",
        headers=manager_headers,
    )
    listed = client.get("/api/inventory", headers=manager_headers)
    persisted_item = next(
        item for item in listed.json()
        if item["id"] == component_id
    )
    for item in (reopened.json(), persisted_item):
        assert item["quantity"] == 12
        assert item["unit_price"] == 14.75
        assert item["supplier"] == "New Supplier"
        assert item["reorder_level"] == 4


def test_staff_cannot_update_component(client, admin_token, staff_token):
    headers = auth(admin_token)
    original = client.get("/api/inventory/1", headers=headers).json()

    response = client.patch(
        "/api/inventory/1",
        json={
            "quantity": 99,
            "unit_price": 99.99,
            "supplier": "Unauthorized Supplier",
            "reorder_level": 99,
        },
        headers=auth(staff_token),
    )

    assert response.status_code == 403
    unchanged = client.get("/api/inventory/1", headers=headers).json()
    assert unchanged["quantity"] == original["quantity"]
    assert unchanged["unit_price"] == original["unit_price"]
    assert unchanged["supplier"] == original["supplier"]
    assert unchanged["reorder_level"] == original["reorder_level"]


@pytest.mark.parametrize(
    "payload",
    [
        {"quantity": -1},
        {"unit_price": -0.01},
        {"reorder_level": -1},
        {"supplier": "   "},
    ],
)
def test_invalid_component_updates_are_rejected(
    client, admin_token, payload
):
    headers = auth(admin_token)
    original = client.get("/api/inventory/1", headers=headers).json()

    response = client.patch(
        "/api/inventory/1",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 422
    unchanged = client.get("/api/inventory/1", headers=headers).json()
    assert unchanged["quantity"] == original["quantity"]
    assert unchanged["unit_price"] == original["unit_price"]
    assert unchanged["supplier"] == original["supplier"]
    assert unchanged["reorder_level"] == original["reorder_level"]


def test_admin_can_add_update_delete_and_audit(client, admin_token):
    h = auth(admin_token)

    payload = {
        "name": "Test MCU",
        "category": "Microcontroller",
        "quantity": 3,
        "unit_price": 100,
        "supplier": "Test Supplier",
        "reorder_level": 2,
    }

    created = client.post(
        "/api/inventory",
        json=payload,
        headers=h,
    )
    assert created.status_code == 201

    item = created.json()
    assert item["sku"].startswith("EIMS-")

    updated = client.patch(
        f"/api/inventory/{item['id']}",
        json={"quantity": 2},
        headers=h,
    )
    assert updated.status_code == 200
    assert updated.json()["quantity"] == 2

    deleted = client.delete(
        f"/api/inventory/{item['id']}",
        headers=h,
    )
    assert deleted.status_code == 200

    logs = client.get("/api/audit-logs", headers=h)
    assert logs.status_code == 200
    assert any(
        x["component_id"] == item["id"]
        for x in logs.json()
    )


def test_duplicate_sku_is_impossible_through_create(client, admin_token):
    h = auth(admin_token)

    p = {
        "name": "A",
        "category": "B",
        "quantity": 1,
        "unit_price": 1,
        "supplier": "S",
        "reorder_level": 1,
    }

    a = client.post("/api/inventory", json=p, headers=h)
    b = client.post("/api/inventory", json=p, headers=h)

    assert a.status_code == 201
    assert b.status_code == 201
    assert a.json()["sku"] != b.json()["sku"]


def test_availability_and_dashboard(client, staff_token):
    h = auth(staff_token)

    availability = client.get(
        "/api/reports/availability",
        headers=h,
    )
    assert availability.status_code == 200

    statuses = {x["status"] for x in availability.json()}
    assert {"in-stock", "low-stock", "out-of-stock"} <= statuses

    dash = client.get("/api/dashboard", headers=h).json()
    assert dash["total_components"] == 3
    assert dash["total_stock_value"] == 13780.0
    assert dash["low_stock_count"] == 1
    assert [item["name"] for item in dash["low_stock_components"]] == [
        "ESP32 Dev Board"
    ]
    assert len(dash["recently_added"]) == 3
    assert {item["name"] for item in dash["recently_added"]} == {
        "Arduino Uno",
        "ESP32 Dev Board",
        "220 Ohm Resistor",
    }
    assert dash["category_stock"] == [
        {"category": "Microcontroller", "quantity": 22, "component_count": 2},
        {"category": "Passive", "quantity": 0, "component_count": 1},
    ]
    assert sum(point["quantity"] for point in dash["stock_trend"]) == 22


def test_dashboard_low_stock_alert_data_updates_after_quantity_change(
    client, admin_token, staff_token
):
    admin_headers = auth(admin_token)
    staff_headers = auth(staff_token)

    before = client.get("/api/dashboard", headers=staff_headers).json()
    assert before["low_stock_count"] == 1

    updated = client.patch(
        "/api/inventory/1",
        json={"quantity": 4},
        headers=admin_headers,
    )
    assert updated.status_code == 200

    after = client.get("/api/dashboard", headers=staff_headers).json()
    assert after["low_stock_count"] == 2
    assert {item["name"] for item in after["low_stock_components"]} == {
        "Arduino Uno",
        "ESP32 Dev Board",
    }


def test_deleted_sku_is_not_reused(client, admin_token):
    headers = auth(admin_token)

    payload = {
        "name": "Temporary Component",
        "category": "Test",
        "quantity": 2,
        "unit_price": 100,
        "supplier": "Test Supplier",
        "reorder_level": 1,
    }

    first = client.post(
        "/api/inventory",
        json=payload,
        headers=headers,
    )

    assert first.status_code == 201
    first_sku = first.json()["sku"]

    deleted = client.delete(
        f"/api/inventory/{first.json()['id']}",
        headers=headers,
    )
    assert deleted.status_code == 200

    second = client.post(
        "/api/inventory",
        json=payload,
        headers=headers,
    )

    assert second.status_code == 201
    assert second.json()["sku"] != first_sku


def test_sku_is_preserved_after_component_update(client, admin_token):
    headers = auth(admin_token)

    payload = {
        "name": "Update Test Component",
        "category": "Test",
        "quantity": 5,
        "unit_price": 50,
        "supplier": "Test Supplier",
        "reorder_level": 2,
    }

    created = client.post(
        "/api/inventory",
        json=payload,
        headers=headers,
    )

    assert created.status_code == 201
    original_sku = created.json()["sku"]

    updated = client.patch(
        f"/api/inventory/{created.json()['id']}",
        json={"quantity": 10},
        headers=headers,
    )

    assert updated.status_code == 200
    assert updated.json()["sku"] == original_sku
    assert updated.json()["quantity"] == 10


def test_sku_is_returned_in_inventory_list(client, admin_token):
    headers = auth(admin_token)

    payload = {
        "name": "List Test Component",
        "category": "Test",
        "quantity": 3,
        "unit_price": 25,
        "supplier": "Test Supplier",
        "reorder_level": 1,
    }

    created = client.post(
        "/api/inventory",
        json=payload,
        headers=headers,
    )

    assert created.status_code == 201
    created_sku = created.json()["sku"]

    inventory = client.get(
        "/api/inventory",
        headers=headers,
    )

    assert inventory.status_code == 200
    assert any(
        item["sku"] == created_sku
        for item in inventory.json()
    )


def test_inventory_list_shows_all_required_fields_and_only_active_items(
    client, staff_token
):
    from app.db import SessionLocal
    from app.models import Component

    headers = auth(staff_token)

    # Add an inactive component that must not appear in inventory.
    db = SessionLocal()
    try:
        db.add(
            Component(
                sku="EIMS-99999",
                name="Inactive Test Component",
                category="Test",
                quantity=10,
                unit_price=99.0,
                supplier="Test Supplier",
                reorder_level=3,
                active=False,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/inventory", headers=headers)

    assert response.status_code == 200
    items = response.json()

    assert len(items) == 3

    item = next(c for c in items if c["sku"] == "EIMS-00001")

    assert item["name"] == "Arduino Uno"
    assert item["sku"] == "EIMS-00001"
    assert item["category"] == "Microcontroller"
    assert item["quantity"] == 18
    assert item["unit_price"] == 650
    assert item["supplier"] == "TechSource"
    assert item["reorder_level"] == 5

    assert all(c["sku"] != "EIMS-99999" for c in items)


@pytest.mark.parametrize(
    ("sort", "expected_skus"),
    [
        ("name", ["EIMS-00003", "EIMS-00001", "EIMS-00002"]),
        ("-name", ["EIMS-00002", "EIMS-00001", "EIMS-00003"]),
        ("quantity", ["EIMS-00002", "EIMS-00003", "EIMS-00001"]),
        ("-quantity", ["EIMS-00001", "EIMS-00003", "EIMS-00002"]),
        ("unit_price", ["EIMS-00003", "EIMS-00002", "EIMS-00001"]),
        ("-unit_price", ["EIMS-00001", "EIMS-00002", "EIMS-00003"]),
        ("date_added", ["EIMS-00002", "EIMS-00003", "EIMS-00001"]),
        ("-date_added", ["EIMS-00001", "EIMS-00003", "EIMS-00002"]),
    ],
)
def test_inventory_can_be_sorted_by_supported_fields(
    client, admin_token, staff_token, sort, expected_skus
):
    from app.db import SessionLocal
    from app.models import Component

    db = SessionLocal()
    try:
        components = db.query(Component).order_by(Component.id).all()
        sort_values = [
            (30, 9.0, datetime(2024, 1, 1)),
            (10, 5.0, datetime(2022, 1, 1)),
            (20, 1.0, datetime(2023, 1, 1)),
        ]

        for component, (quantity, unit_price, created_at) in zip(
            components, sort_values
        ):
            component.quantity = quantity
            component.unit_price = unit_price
            component.created_at = created_at

        db.commit()
    finally:
        db.close()

    token = admin_token if "date_added" in sort else staff_token
    response = client.get(
        f"/api/inventory?sort={sort}",
        headers=auth(token),
    )

    assert response.status_code == 200
    assert [item["sku"] for item in response.json()] == expected_skus


# EIMS-F-002: Search Components

def test_search_inventory_by_component_name(client, staff_token):
    response = client.get(
        "/api/inventory?search=Arduino%20Uno",
        headers=auth(staff_token),
    )

    assert response.status_code == 200
    items = response.json()

    assert len(items) == 1
    assert items[0]["name"] == "Arduino Uno"
    assert items[0]["sku"] == "EIMS-00001"


def test_search_inventory_by_sku(client, staff_token):
    response = client.get(
        "/api/inventory?search=EIMS-00002",
        headers=auth(staff_token),
    )

    assert response.status_code == 200
    items = response.json()

    assert len(items) == 1
    assert items[0]["sku"] == "EIMS-00002"
    assert items[0]["name"] == "ESP32 Dev Board"


def test_search_inventory_by_category(client, staff_token):
    response = client.get(
        "/api/inventory?search=Microcontroller",
        headers=auth(staff_token),
    )

    assert response.status_code == 200
    items = response.json()

    assert len(items) == 2
    assert all(
        item["category"] == "Microcontroller"
        for item in items
    )


def test_search_inventory_with_no_matches(client, staff_token):
    response = client.get(
        "/api/inventory?search=NonexistentComponent123",
        headers=auth(staff_token),
    )

    assert response.status_code == 200
    assert response.json() == []

def test_filter_inventory_by_category(client, staff_token):
    response = client.get(
        "/api/inventory?category=Microcontroller",
        headers=auth(staff_token),
    )

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert all(item["category"] == "Microcontroller" for item in items)


def test_filter_inventory_by_supplier(client, staff_token):
    response = client.get(
        "/api/inventory?supplier=CircuitHub",
        headers=auth(staff_token),
    )

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert all(item["supplier"] == "CircuitHub" for item in items)


def test_filter_inventory_by_stock_status(client, staff_token):
    response = client.get(
        "/api/inventory?status=low-stock",
        headers=auth(staff_token),
    )

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["name"] == "ESP32 Dev Board"


def test_filter_inventory_with_combined_criteria(client, staff_token):
    response = client.get(
        "/api/inventory?category=Passive&supplier=CircuitHub&status=out-of-stock",
        headers=auth(staff_token),
    )

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["name"] == "220 Ohm Resistor"


def test_filter_inventory_with_no_matches(client, staff_token):
    response = client.get(
        "/api/inventory?category=Microcontroller&supplier=CircuitHub",
        headers=auth(staff_token),
    )

    assert response.status_code == 200
    assert response.json() == []