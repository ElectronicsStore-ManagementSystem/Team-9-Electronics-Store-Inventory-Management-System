
import pytest


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    "username",
    [
        "' OR '1'='1",
        "' OR 1=1 --",
        "admin' --",
        "'; DROP TABLE users; --",
    ],
)
def test_sql_injection_login_attempts_are_rejected(client, username):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.parametrize(
    "search",
    [
        "' OR '1'='1",
        "' UNION SELECT * FROM users --",
        "'; DROP TABLE components; --",
    ],
)
def test_sql_injection_inventory_search_does_not_bypass_filters(
    client, staff_token, search
):
    response = client.get(
        "/api/inventory",
        params={"search": search},
        headers=auth(staff_token),
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    "sort",
    [
        "name; DROP TABLE components",
        "name DESC; SELECT * FROM users",
        "' OR '1'='1",
    ],
)
def test_malicious_sort_parameters_are_rejected(client, staff_token, sort):
    response = client.get(
        "/api/inventory",
        params={"sort": sort},
        headers=auth(staff_token),
    )

    assert response.status_code == 422


def test_oversized_search_input_is_limited(client, staff_token):
    search = "A" * 200

    response = client.get(
        "/api/inventory",
        params={"search": search},
        headers=auth(staff_token),
    )

    assert response.status_code == 200
    assert response.json() == []




def test_component_creation_rejects_untrusted_image_url(client, admin_token):
    response = client.post(
        "/api/inventory",
        headers=auth(admin_token),
        json={
            "name": "Image URL Security Test",
            "category": "Security",
            "quantity": 1,
            "unit_price": 10,
            "supplier": "Security Test Supplier",
            "image_url": "javascript:alert(1)",
        },
    )

    assert response.status_code == 422



def test_component_creation_handles_html_like_text_safely(client, admin_token):
    payload = {
        "name": "<script>alert(1)</script>",
        "category": "<img src=x onerror=alert(1)>",
        "quantity": 1,
        "unit_price": 10,
        "supplier": "<b>Test Supplier</b>",
    }

    response = client.post(
        "/api/inventory",
        headers=auth(admin_token),
        json=payload,
    )

    assert response.status_code == 201
    component = response.json()

    # The API stores text; the frontend must escape it when rendering HTML.
    assert component["name"] == payload["name"]
    assert component["category"] == payload["category"]
    assert component["supplier"] == payload["supplier"]
