import io

import pytest
from PIL import Image

from app import main


@pytest.fixture
def image_upload_dir(tmp_path, monkeypatch):
    upload_dir = tmp_path / "components"
    upload_dir.mkdir()

    monkeypatch.setattr(main, "UPLOAD_DIR", upload_dir)

    return upload_dir


def create_png():
    image_bytes = io.BytesIO()

    image = Image.new("RGB", (10, 10), color="red")
    image.save(image_bytes, format="PNG")
    image_bytes.seek(0)

    return image_bytes


def test_upload_component_image(client, admin_token, image_upload_dir):
    response = client.post(
        "/api/inventory/1/image",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "file": ("test.png", create_png(), "image/png")
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["image_url"].startswith("/uploads/components/")

    saved_file = image_upload_dir / data["image_url"].split("/")[-1]
    assert saved_file.exists()


def test_replace_component_image(client, admin_token, image_upload_dir):
    headers = {"Authorization": f"Bearer {admin_token}"}

    first_response = client.post(
        "/api/inventory/1/image",
        headers=headers,
        files={"file": ("first.png", create_png(), "image/png")},
    )

    assert first_response.status_code == 200

    first_url = first_response.json()["image_url"]
    first_file = image_upload_dir / first_url.split("/")[-1]

    second_response = client.post(
        "/api/inventory/1/image",
        headers=headers,
        files={"file": ("second.png", create_png(), "image/png")},
    )

    assert second_response.status_code == 200

    second_url = second_response.json()["image_url"]

    assert second_url != first_url
    assert not first_file.exists()
    assert (image_upload_dir / second_url.split("/")[-1]).exists()


def test_remove_component_image(client, admin_token, image_upload_dir):
    headers = {"Authorization": f"Bearer {admin_token}"}

    upload_response = client.post(
        "/api/inventory/1/image",
        headers=headers,
        files={"file": ("test.png", create_png(), "image/png")},
    )

    assert upload_response.status_code == 200

    image_url = upload_response.json()["image_url"]
    image_file = image_upload_dir / image_url.split("/")[-1]

    remove_response = client.delete(
        "/api/inventory/1/image",
        headers=headers,
    )

    assert remove_response.status_code == 200
    assert remove_response.json()["image_url"] is None
    assert not image_file.exists()

    component_response = client.get(
        "/api/inventory/1",
        headers=headers,
    )

    assert component_response.status_code == 200
    assert component_response.json()["image_url"] is None


def test_reject_unsupported_image_format(client, admin_token):
    response = client.post(
        "/api/inventory/1/image",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "file": ("test.gif", b"fake image", "image/gif")
        },
    )

    assert response.status_code == 415


def test_reject_image_larger_than_5mb(client, admin_token):
    large_file = b"x" * (5 * 1024 * 1024 + 1)

    response = client.post(
        "/api/inventory/1/image",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "file": ("large.png", large_file, "image/png")
        },
    )

    assert response.status_code == 413


def test_staff_cannot_remove_component_image(client, staff_token):
    response = client.delete(
        "/api/inventory/1/image",
        headers={"Authorization": f"Bearer {staff_token}"},
    )

    assert response.status_code == 403


def test_remove_image_when_none_exists(client, admin_token):
    response = client.delete(
        "/api/inventory/1/image",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404