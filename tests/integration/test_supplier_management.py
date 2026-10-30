def auth(token):
    return {"Authorization": "Bearer " + token}


def test_supplier_can_be_created_and_used_in_inventory_filters(
    client, admin_token
):
    headers = auth(admin_token)
    created_supplier = client.post(
        "/api/suppliers",
        json={"name": "Northstar Components"},
        headers=headers,
    )

    assert created_supplier.status_code == 201
    assert created_supplier.json()["name"] == "Northstar Components"
    assert "Northstar Components" in client.get(
        "/api/suppliers",
        headers=headers,
    ).json()

    created_component = client.post(
        "/api/inventory",
        json={
            "name": "Northstar Sensor",
            "category": "New Sensors",
            "quantity": 8,
            "unit_price": 12.5,
            "supplier": "Northstar Components",
            "reorder_level": 2,
        },
        headers=headers,
    )
    assert created_component.status_code == 201

    assert "New Sensors" in client.get(
        "/api/categories",
        headers=headers,
    ).json()
    filtered = client.get(
        "/api/inventory",
        params={
            "category": "New Sensors",
            "supplier": "Northstar Components",
        },
        headers=headers,
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [
        created_component.json()["id"]
    ]


def test_duplicate_supplier_is_rejected_case_insensitively(
    client, admin_token
):
    headers = auth(admin_token)
    first = client.post(
        "/api/suppliers",
        json={"name": "Unique Supplier"},
        headers=headers,
    )
    duplicate = client.post(
        "/api/suppliers",
        json={"name": "unique supplier"},
        headers=headers,
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409


def test_existing_component_suppliers_cannot_be_added_as_duplicates(
    client, admin_token
):
    response = client.post(
        "/api/suppliers",
        json={"name": "techsource"},
        headers=auth(admin_token),
    )

    assert response.status_code == 409


def test_supplier_creation_validates_required_name(client, admin_token):
    response = client.post(
        "/api/suppliers",
        json={"name": "   "},
        headers=auth(admin_token),
    )

    assert response.status_code == 422


def test_staff_cannot_create_supplier(client, staff_token):
    response = client.post(
        "/api/suppliers",
        json={"name": "Unauthorized Supplier"},
        headers=auth(staff_token),
    )

    assert response.status_code == 403


def test_manager_can_create_supplier(client):
    from app.db import SessionLocal
    from app.models import User
    from app.security import hash_password

    db = SessionLocal()
    try:
        db.add(
            User(
                username="supplier_manager",
                password_hash=hash_password("Manager@12345"),
                role="MANAGER",
            )
        )
        db.commit()
    finally:
        db.close()

    login = client.post(
        "/api/auth/login",
        json={
            "username": "supplier_manager",
            "password": "Manager@12345",
        },
    )
    assert login.status_code == 200

    response = client.post(
        "/api/suppliers",
        json={"name": "Manager Supplier"},
        headers=auth(login.json()["access_token"]),
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Manager Supplier"


def test_supplier_and_category_options_require_authentication(client):
    assert client.get("/api/suppliers").status_code == 401
    assert client.get("/api/categories").status_code == 401
