import pytest

from app.db import SessionLocal
from app.models import (
    Component,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderReceipt,
    StockMovement,
    Supplier,
)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def get_component(client, token):
    response = client.get(
        "/api/inventory",
        headers=auth(token),
    )

    assert response.status_code == 200
    components = response.json()
    assert len(components) >= 2

    return components

def create_purchase_order(client, token, components=None, quantities=None):
    if components is None:
        components = get_component(client, token)[:2]

    if quantities is None:
        quantities = [10] * len(components)

    # Check whether a supplier already exists.
    with SessionLocal() as db:
        supplier = db.query(Supplier).first()
        supplier_id = supplier.id if supplier else None

    # Create a supplier if the test database has none.
    if supplier_id is None:
        supplier_response = client.post(
            "/api/suppliers",
            headers=auth(token),
            json={"name": "Purchase Order Test Supplier"},
        )

        assert supplier_response.status_code == 201, supplier_response.text
        supplier_id = supplier_response.json()["id"]

    # Create the purchase order.
    response = client.post(
        "/api/purchase-orders",
        headers=auth(token),
        json={
            "supplier_id": supplier_id,
            "items": [
                {
                    "component_id": component["id"],
                    "ordered_quantity": quantity,
                }
                for component, quantity in zip(components, quantities)
            ],
        },
    )

    return response

def order_purchase_order(client, token, order_id):
    return client.patch(
        f"/api/purchase-orders/{order_id}/status",
        headers=auth(token),
        json={"status": "ORDERED"},
    )


def receive_items(client, token, order, quantities, idempotency_key):
    return client.post(
        f"/api/purchase-orders/{order['id']}/receive",
        headers=auth(token),
        json={
            "idempotency_key": idempotency_key,
            "items": [
                {
                    "purchase_order_item_id": item["id"],
                    "received_quantity": quantity,
                }
                for item, quantity in zip(order["items"], quantities)
            ],
        },
    )


# TC01: Create a purchase order for an existing supplier.

def test_create_purchase_order(client, admin_token):
    response = create_purchase_order(client, admin_token)

    assert response.status_code == 201

    order = response.json()
    assert order["id"] is not None
    assert order["order_number"].startswith("PO-")
    assert order["status"] == "DRAFT"
    assert len(order["items"]) == 2


# TC02: Purchase order supports multiple components.

def test_purchase_order_supports_multiple_components(client, admin_token):
    components = get_component(client, admin_token)[:2]

    response = create_purchase_order(
        client,
        admin_token,
        components,
        [15, 25],
    )

    assert response.status_code == 201

    items = response.json()["items"]

    assert len(items) == 2
    assert items[0]["ordered_quantity"] == 15
    assert items[1]["ordered_quantity"] == 25


# TC03: Every purchase order gets a unique order number.

def test_purchase_order_numbers_are_unique(client, admin_token):
    first = create_purchase_order(client, admin_token)
    second = create_purchase_order(client, admin_token)

    assert first.status_code == 201
    assert second.status_code == 201

    assert first.json()["order_number"] != second.json()["order_number"]


# TC04: Purchase order status is persisted.

def test_purchase_order_status_persists(client, admin_token):
    created = create_purchase_order(client, admin_token)
    assert created.status_code == 201

    order_id = created.json()["id"]

    updated = order_purchase_order(
        client,
        admin_token,
        order_id,
    )

    assert updated.status_code == 200
    assert updated.json()["status"] == "ORDERED"

    fetched = client.get(
        f"/api/purchase-orders/{order_id}",
        headers=auth(admin_token),
    )

    assert fetched.status_code == 200
    assert fetched.json()["status"] == "ORDERED"


# TC05: Full receipt increases inventory by the received quantity.

def test_full_receipt_updates_inventory(client, admin_token):
    components = get_component(client, admin_token)[:2]

    initial_quantities = {
        component["id"]: component["quantity"]
        for component in components
    }

    created = create_purchase_order(
        client,
        admin_token,
        components,
        [10, 20],
    )

    assert created.status_code == 201
    order = created.json()

    ordered = order_purchase_order(
        client,
        admin_token,
        order["id"],
    )
    assert ordered.status_code == 200

    received = receive_items(
        client,
        admin_token,
        order,
        [10, 20],
        "full-receipt-001",
    )
    assert received.status_code == 200
    assert len(received.json()) == 2
    assert [receipt["received_quantity"] for receipt in received.json()] == [10, 20]

    order_details = client.get(
        f"/api/purchase-orders/{order['id']}",
        headers=auth(admin_token),
    )
    assert order_details.status_code == 200
    assert order_details.json()["status"] == "RECEIVED"

    for component, quantity in zip(components, [10, 20]):
        updated = client.get(
            f"/api/inventory/{component['id']}",
            headers=auth(admin_token),
        )

        assert updated.status_code == 200
        assert updated.json()["quantity"] == (
            initial_quantities[component["id"]] + quantity
        )


# TC06: Partial delivery adds only the actually received quantity.

def test_partial_receipt_updates_only_received_quantity(
    client,
    admin_token,
):
    components = get_component(client, admin_token)[:1]
    component = components[0]

    initial_quantity = component["quantity"]

    created = create_purchase_order(
        client,
        admin_token,
        components,
        [20],
    )

    assert created.status_code == 201
    order = created.json()

    assert order_purchase_order(
        client,
        admin_token,
        order["id"],
    ).status_code == 200

    received = receive_items(
        client,
        admin_token,
        order,
        [7],
        "partial-receipt-001",
    )

    assert received.status_code == 200
    assert len(received.json()) == 1
    assert received.json()[0]["received_quantity"] == 7

    order_details = client.get(
        f"/api/purchase-orders/{order['id']}",
        headers=auth(admin_token),
    )
    assert order_details.status_code == 200
    assert order_details.json()["status"] == "PARTIALLY_RECEIVED"

    updated = client.get(
        f"/api/inventory/{component['id']}",
        headers=auth(admin_token),
    )

    assert updated.json()["quantity"] == initial_quantity + 7


# TC07: Remaining delivery completes the purchase order.

def test_remaining_delivery_changes_status_to_received(
    client,
    admin_token,
):
    components = get_component(client, admin_token)[:1]

    created = create_purchase_order(
        client,
        admin_token,
        components,
        [20],
    )

    assert created.status_code == 201
    order = created.json()

    assert order_purchase_order(
        client,
        admin_token,
        order["id"],
    ).status_code == 200

    first_receipt = receive_items(
        client,
        admin_token,
        order,
        [8],
        "remaining-receipt-001",
    )

    assert first_receipt.status_code == 200
    assert len(first_receipt.json()) == 1
    assert first_receipt.json()[0]["received_quantity"] == 8

    order_details = client.get(
        f"/api/purchase-orders/{order['id']}",
        headers=auth(admin_token),
    )
    assert order_details.status_code == 200
    assert order_details.json()["status"] == "PARTIALLY_RECEIVED"

    second_receipt = client.post(
        f"/api/purchase-orders/{order['id']}/receive",
        headers=auth(admin_token),
        json={
            "idempotency_key": "remaining-receipt-002",
            "items": [
                {
                    "purchase_order_item_id": order["items"][0]["id"],
                    "received_quantity": 12,
                }
            ],
        },
    )

    assert second_receipt.status_code == 200
    assert len(second_receipt.json()) == 1
    assert second_receipt.json()[0]["received_quantity"] == 12

    final_order_details = client.get(
        f"/api/purchase-orders/{order['id']}",
        headers=auth(admin_token),
    )
    assert final_order_details.status_code == 200
    assert final_order_details.json()["status"] == "RECEIVED"


# TC08: Receiving more than the outstanding quantity is rejected.

def test_over_receiving_is_rejected(client, admin_token):
    components = get_component(client, admin_token)[:1]

    created = create_purchase_order(
        client,
        admin_token,
        components,
        [10],
    )

    assert created.status_code == 201
    order = created.json()

    assert order_purchase_order(
        client,
        admin_token,
        order["id"],
    ).status_code == 200

    response = receive_items(
        client,
        admin_token,
        order,
        [11],
        "over-receipt-001",
    )

    assert response.status_code == 400


# TC09: Repeating the same receiving request does not add stock twice.

def test_duplicate_receiving_does_not_update_stock_twice(
    client,
    admin_token,
):
    components = get_component(client, admin_token)[:1]
    component = components[0]

    initial_quantity = component["quantity"]

    created = create_purchase_order(
        client,
        admin_token,
        components,
        [10],
    )

    assert created.status_code == 201
    order = created.json()

    assert order_purchase_order(
        client,
        admin_token,
        order["id"],
    ).status_code == 200

    first = receive_items(
        client,
        admin_token,
        order,
        [5],
        "duplicate-receipt-001",
    )

    assert first.status_code == 200

    duplicate = receive_items(
        client,
        admin_token,
        order,
        [5],
        "duplicate-receipt-001",
    )

    assert duplicate.status_code == 409

    updated = client.get(
        f"/api/inventory/{component['id']}",
        headers=auth(admin_token),
    )

    assert updated.json()["quantity"] == initial_quantity + 5


# TC10: Cancelled purchase orders cannot receive stock.

def test_cancelled_purchase_order_cannot_receive_stock(
    client,
    admin_token,
):
    components = get_component(client, admin_token)[:1]
    component = components[0]

    initial_quantity = component["quantity"]

    created = create_purchase_order(
        client,
        admin_token,
        components,
        [10],
    )

    assert created.status_code == 201
    order = created.json()

    cancelled = client.patch(
        f"/api/purchase-orders/{order['id']}/status",
        headers=auth(admin_token),
        json={"status": "CANCELLED"},
    )

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"

    response = receive_items(
        client,
        admin_token,
        order,
        [5],
        "cancelled-receipt-001",
    )

    assert response.status_code == 409

    updated = client.get(
        f"/api/inventory/{component['id']}",
        headers=auth(admin_token),
    )

    assert updated.json()["quantity"] == initial_quantity


# TC11: Staff cannot create, update, or receive purchase orders.

def test_staff_cannot_perform_purchase_order_operations(
    client,
    admin_token,
    staff_token,
):
    created = create_purchase_order(client, admin_token)

    assert created.status_code == 201
    order = created.json()

    create_attempt = create_purchase_order(client, staff_token)
    assert create_attempt.status_code == 403

    status_attempt = client.patch(
        f"/api/purchase-orders/{order['id']}/status",
        headers=auth(staff_token),
        json={"status": "ORDERED"},
    )

    assert status_attempt.status_code == 403

    receive_attempt = receive_items(
        client,
        staff_token,
        order,
        [1, 1],
        "staff-receipt-001",
    )

    assert receive_attempt.status_code == 403


# TC12: A receiving failure rolls back inventory and receipt history.

def test_receiving_failure_rolls_back_all_changes(
    client,
    admin_token,
    monkeypatch,
):
    from app import main

    components = get_component(client, admin_token)[:1]
    component = components[0]

    initial_quantity = component["quantity"]

    created = create_purchase_order(
        client,
        admin_token,
        components,
        [10],
    )

    assert created.status_code == 201
    order = created.json()

    assert order_purchase_order(
        client,
        admin_token,
        order["id"],
    ).status_code == 200

    def fail_receipt_creation(*args, **kwargs):
        raise RuntimeError("Simulated receiving failure")

    monkeypatch.setattr(
        main.repositories,
        "create_purchase_order_receipt",
        fail_receipt_creation,
    )

    response = receive_items(
        client,
        admin_token,
        order,
        [5],
        "rollback-receipt-001",
    )

    assert response.status_code == 500

    with SessionLocal() as db:
        updated_component = db.get(Component, component["id"])
        updated_order = db.get(PurchaseOrder, order["id"])

        updated_item = (
            db.query(PurchaseOrderItem)
            .filter_by(purchase_order_id=order["id"])
            .first()
        )

        receipts = (
            db.query(PurchaseOrderReceipt)
            .filter_by(purchase_order_item_id=updated_item.id)
            .all()
        )

        movements = (
            db.query(StockMovement)
            .filter_by(
                component_id=component["id"],
                reason=f"Purchase order {order['order_number']} received",
            )
            .all()
        )

        assert updated_component.quantity == initial_quantity
        assert updated_item.received_quantity == 0
        assert updated_order.status == "ORDERED"
        assert len(receipts) == 0
        assert len(movements) == 0