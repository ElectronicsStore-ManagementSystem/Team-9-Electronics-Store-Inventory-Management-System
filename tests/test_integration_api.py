def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_unauthenticated_inventory_is_rejected(client):
    r = client.get("/api/inventory")
    assert r.status_code == 401


def test_staff_can_read_inventory(client, staff_token):
    r = client.get(
        "/api/inventory",
        headers=auth(staff_token),
    )
    assert r.status_code == 200
    assert len(r.json()) == 3


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

    assert client.delete(
        "/api/inventory/1",
        headers=h,
    ).status_code == 403


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
    assert dash["low_stock_count"] == 1


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

    # The three seeded active components should remain visible.
    assert len(items) == 3

    item = next(c for c in items if c["sku"] == "EIMS-00001")

    assert item["name"] == "Arduino Uno"
    assert item["sku"] == "EIMS-00001"
    assert item["category"] == "Microcontroller"
    assert item["quantity"] == 18
    assert item["unit_price"] == 650
    assert item["supplier"] == "TechSource"
    assert item["reorder_level"] == 5

    # Inactive components must not appear.
    assert all(c["sku"] != "EIMS-99999" for c in items)


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