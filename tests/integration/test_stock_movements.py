def auth(token):
    return {"Authorization": f"Bearer {token}"}


def get_component(client, token):
    response = client.get(
        "/api/inventory",
        headers=auth(token),
    )

    assert response.status_code == 200
    components = response.json()
    assert components

    return components[0]


def test_stock_in_increases_component_quantity(client, admin_token):
    component = get_component(client, admin_token)
    component_id = component["id"]
    initial_quantity = component["quantity"]

    response = client.post(
        f"/api/inventory/{component_id}/movements",
        headers=auth(admin_token),
        json={
            "movement_type": "STOCK_IN",
            "quantity": 10,
            "reason": "New stock received",
        },
    )

    assert response.status_code == 201
    assert response.json()["movement_type"] == "STOCK_IN"

    updated = client.get(
        f"/api/inventory/{component_id}",
        headers=auth(admin_token),
    )

    assert updated.status_code == 200
    assert updated.json()["quantity"] == initial_quantity + 10


def test_stock_out_decreases_component_quantity(client, admin_token):
    component = get_component(client, admin_token)
    component_id = component["id"]
    initial_quantity = component["quantity"]

    assert initial_quantity > 0

    response = client.post(
        f"/api/inventory/{component_id}/movements",
        headers=auth(admin_token),
        json={
            "movement_type": "STOCK_OUT",
            "quantity": 1,
            "reason": "Component sold",
        },
    )

    assert response.status_code == 201

    updated = client.get(
        f"/api/inventory/{component_id}",
        headers=auth(admin_token),
    )

    assert updated.status_code == 200
    assert updated.json()["quantity"] == initial_quantity - 1

    def test_stock_movement_metadata_is_recorded(client, admin_token):
        component = get_component(client, admin_token)
        component_id = component["id"]

    response = client.post(
        f"/api/inventory/{component_id}/movements",
        headers=auth(admin_token),
        json={
            "movement_type": "STOCK_IN",
            "quantity": 5,
            "reason": "Supplier delivery",
        },
    )

    assert response.status_code == 201

    movement = response.json()

    assert movement["component_id"] == component_id
    assert movement["component_name"] == component["name"]
    assert movement["movement_type"] == "STOCK_IN"
    assert movement["quantity"] == 5
    assert movement["reason"] == "Supplier delivery"
    assert movement["user_id"] is not None
    assert movement["timestamp"] is not None


def test_stock_movement_metadata_is_recorded(client, admin_token):
    component = get_component(client, admin_token)
    component_id = component["id"]

    response = client.post(
        f"/api/inventory/{component_id}/movements",
        headers=auth(admin_token),
        json={
            "movement_type": "STOCK_IN",
            "quantity": 5,
            "reason": "Supplier delivery",
        },
    )

    assert response.status_code == 201

    movement = response.json()

    assert movement["component_id"] == component_id
    assert movement["component_name"] == component["name"]
    assert movement["movement_type"] == "STOCK_IN"
    assert movement["quantity"] == 5
    assert movement["reason"] == "Supplier delivery"
    assert movement["user_id"] is not None
    assert movement["timestamp"] is not None

def test_stock_movement_persists_in_history(client, admin_token):
    component = get_component(client, admin_token)
    component_id = component["id"]

    client.post(
        f"/api/inventory/{component_id}/movements",
        headers=auth(admin_token),
        json={
            "movement_type": "STOCK_IN",
            "quantity": 7,
            "reason": "Persistence test",
        },
    )

    response = client.get(
        f"/api/inventory/{component_id}/movements",
        headers=auth(admin_token),
    )

    assert response.status_code == 200

    movements = response.json()

    assert any(
        movement["quantity"] == 7
        and movement["reason"] == "Persistence test"
        for movement in movements
    )


def test_history_contains_only_requested_component_movements(
    client, admin_token
):
    components_response = client.get(
        "/api/inventory",
        headers=auth(admin_token),
    )

    components = components_response.json()
    assert len(components) >= 2

    first_id = components[0]["id"]
    second_id = components[1]["id"]

    client.post(
        f"/api/inventory/{first_id}/movements",
        headers=auth(admin_token),
        json={
            "movement_type": "STOCK_IN",
            "quantity": 3,
            "reason": "First component",
        },
    )

    client.post(
        f"/api/inventory/{second_id}/movements",
        headers=auth(admin_token),
        json={
            "movement_type": "STOCK_IN",
            "quantity": 4,
            "reason": "Second component",
        },
    )

    response = client.get(
        f"/api/inventory/{first_id}/movements",
        headers=auth(admin_token),
    )

    assert response.status_code == 200

    movements = response.json()

    assert movements
    assert all(m["component_id"] == first_id for m in movements)



def test_invalid_stock_movement_quantities_are_rejected(client, admin_token):
    component = get_component(client, admin_token)
    component_id = component["id"]

    for quantity in [0, -5]:
        response = client.post(
            f"/api/inventory/{component_id}/movements",
            headers=auth(admin_token),
            json={
                "movement_type": "STOCK_IN",
                "quantity": quantity,
                "reason": "Invalid quantity test",
            },
        )

        assert response.status_code == 422


def test_stock_movement_failure_rolls_back_quantity(client, admin_token, monkeypatch):
    from app import main
    from app.db import SessionLocal
    from app.models import Component, StockMovement

    component = get_component(client, admin_token)
    component_id = component["id"]
    initial_quantity = component["quantity"]

    def fail_movement_creation(*args, **kwargs):
        raise RuntimeError("Simulated database failure")

    monkeypatch.setattr(
        main.repositories,
        "create_stock_movement",
        fail_movement_creation,
    )

    response = client.post(
        f"/api/inventory/{component_id}/movements",
        headers=auth(admin_token),
        json={
            "movement_type": "STOCK_IN",
            "quantity": 10,
            "reason": "Rollback test",
        },
    )

    assert response.status_code == 500

    with SessionLocal() as db:
        updated_component = db.get(Component, component_id)

        assert updated_component.quantity == initial_quantity

        movements = (
            db.query(StockMovement)
            .filter_by(
                component_id=component_id,
                reason="Rollback test",
            )
            .all()
        )

        assert len(movements) == 0



def test_staff_cannot_record_stock_movements(client, staff_token, admin_token):
    component = get_component(client, admin_token)
    component_id = component["id"]

    response = client.post(
        f"/api/inventory/{component_id}/movements",
        headers=auth(staff_token),
        json={
            "movement_type": "STOCK_IN",
            "quantity": 5,
            "reason": "Unauthorized attempt",
        },
    )

    assert response.status_code == 403


def test_stock_movement_records_cannot_be_modified_or_deleted(
    client, admin_token
):
    component = get_component(client, admin_token)
    component_id = component["id"]

    create_response = client.post(
        f"/api/inventory/{component_id}/movements",
        headers=auth(admin_token),
        json={
            "movement_type": "STOCK_IN",
            "quantity": 5,
            "reason": "Immutable history test",
        },
    )

    assert create_response.status_code == 201
    movement_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/inventory/{component_id}/movements/{movement_id}",
        headers=auth(admin_token),
        json={"reason": "Modified reason"},
    )

    delete_response = client.delete(
        f"/api/inventory/{component_id}/movements/{movement_id}",
        headers=auth(admin_token),
    )

    assert update_response.status_code in (404, 405)
    assert delete_response.status_code in (404, 405)
