def test_branch_options_are_available_to_authenticated_users(
    client, staff_token
):
    response = client.get(
        "/api/branches",
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    assert response.status_code == 200
    assert response.json() == ["Main Branch"]


def test_manager_can_add_branch_and_assign_components(
    client, admin_token
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    created_branch = client.post(
        "/api/branches",
        json={"name": "Downtown Branch"},
        headers=headers,
    )

    assert created_branch.status_code == 201
    assert created_branch.json()["name"] == "Downtown Branch"

    created_component = client.post(
        "/api/inventory",
        json={
            "name": "Branch stock item",
            "category": "Components",
            "quantity": 3,
            "unit_price": 12.5,
            "supplier": "Example Supplier",
            "branch": "Downtown Branch",
        },
        headers=headers,
    )

    assert created_component.status_code == 201
    assert created_component.json()["branch"] == "Downtown Branch"

    filtered_components = client.get(
        "/api/inventory?branch=Downtown%20Branch",
        headers=headers,
    )

    assert filtered_components.status_code == 200
    assert [item["name"] for item in filtered_components.json()] == [
        "Branch stock item"
    ]

    updated_component = client.patch(
        f"/api/inventory/{created_component.json()['id']}",
        json={"branch": "main branch"},
        headers=headers,
    )

    assert updated_component.status_code == 200
    assert updated_component.json()["branch"] == "Main Branch"


def test_branch_names_are_unique_case_insensitively(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    first = client.post(
        "/api/branches",
        json={"name": "North Area"},
        headers=headers,
    )
    duplicate = client.post(
        "/api/branches",
        json={"name": "north area"},
        headers=headers,
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409


def test_component_cannot_be_assigned_to_unknown_branch(
    client, admin_token
):
    response = client.post(
        "/api/inventory",
        json={
            "name": "Unassigned item",
            "category": "Components",
            "quantity": 1,
            "unit_price": 10,
            "supplier": "Example Supplier",
            "branch": "Unknown Branch",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Choose a branch from the branch list."


def test_staff_cannot_add_branches(client, staff_token):
    response = client.post(
        "/api/branches",
        json={"name": "Restricted Branch"},
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    assert response.status_code == 403
