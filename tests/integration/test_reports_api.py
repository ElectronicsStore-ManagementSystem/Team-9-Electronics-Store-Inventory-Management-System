from fastapi.testclient import TestClient


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_search_inventory_by_component_name(client, staff_token):
    response = client.get(
        "/api/inventory?search=Arduino Uno",
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



def test_availability_report_classifies_all_stock_statuses(client, staff_token):
    response = client.get(
        "/api/reports/availability",
        headers=auth(staff_token),
    )

    assert response.status_code == 200

    items = {item["name"]: item for item in response.json()}

    assert items["Arduino Uno"]["status"] == "in-stock"
    assert items["ESP32 Dev Board"]["status"] == "low-stock"
    assert items["220 Ohm Resistor"]["status"] == "out-of-stock"


def test_availability_report_reflects_updated_quantity(client, admin_token):
    headers = auth(admin_token)

    # Get the current component details.
    response = client.get("/api/reports/availability", headers=headers)
    assert response.status_code == 200

    arduino = next(
        item for item in response.json()
        if item["name"] == "Arduino Uno"
    )

    # Change its quantity to zero.
    update = client.patch(
        f"/api/inventory/{arduino['id']}",
        json={"quantity": 0},
        headers=headers,
    )
    assert update.status_code == 200

    # The report should show the updated quantity and status.
    report = client.get("/api/reports/availability", headers=headers)
    updated_arduino = next(
        item for item in report.json()
        if item["name"] == "Arduino Uno"
    )

    assert updated_arduino["quantity"] == 0
    assert updated_arduino["status"] == "out-of-stock"


def test_availability_report_excludes_inactive_components(client, admin_token):
    headers = auth(admin_token)

    response = client.get("/api/reports/availability", headers=headers)
    arduino = next(
        item for item in response.json()
        if item["name"] == "Arduino Uno"
    )

    # Delete the component (the API marks it inactive).
    deleted = client.delete(
        f"/api/inventory/{arduino['id']}",
        headers=headers,
    )
    assert deleted.status_code == 200

    # Inactive components should not appear in the report.
    report = client.get("/api/reports/availability", headers=headers)
    names = [item["name"] for item in report.json()]

    assert "Arduino Uno" not in names
