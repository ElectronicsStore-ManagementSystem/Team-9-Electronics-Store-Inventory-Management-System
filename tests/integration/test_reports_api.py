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


# Add API-client tests here once the report route is wired into
# the shared app.
def test_report_integration_placeholder():
    assert True