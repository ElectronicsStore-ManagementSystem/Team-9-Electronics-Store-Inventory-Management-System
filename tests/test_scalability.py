from concurrent.futures import ThreadPoolExecutor
from time import perf_counter

from app.db import SessionLocal
from app.models import Component


def _populate_components(count: int) -> None:
    with SessionLocal() as db:
        db.add_all(
            [
                Component(
                    sku=f"LOAD-{index:05d}",
                    name=f"Load Component {index}",
                    category="Load Test",
                    quantity=10,
                    unit_price=1.0,
                    supplier="Load Supplier",
                    reorder_level=2,
                )
                for index in range(1, count + 1)
            ]
        )
        db.commit()


def test_inventory_supports_10000_components_and_20_concurrent_users(
    client, admin_token
):
    _populate_components(10_000)
    headers = {"Authorization": f"Bearer {admin_token}"}

    def request_page(page: int):
        return client.get(
            "/api/inventory",
            params={"search": "Load Component", "limit": 100, "offset": page * 100},
            headers=headers,
        )

    started = perf_counter()
    with ThreadPoolExecutor(max_workers=20) as executor:
        responses = list(executor.map(request_page, range(20)))
    elapsed = perf_counter() - started

    assert all(response.status_code == 200 for response in responses)
    assert all(len(response.json()) == 100 for response in responses)
    assert elapsed < 5
    assert len(
        {
            component["id"]
            for response in responses
            for component in response.json()
        }
    ) == 2_000


def test_dashboard_and_inventory_meet_3_second_target(client, admin_token):
    _populate_components(10_000)

    headers = {"Authorization": f"Bearer {admin_token}"}

    # Warm up both endpoints.
    assert client.get("/api/dashboard", headers=headers).status_code == 200
    assert client.get(
        "/api/inventory",
        params={"search": "Load Component", "limit": 100},
        headers=headers,
    ).status_code == 200

    def measure_request(path, params=None):
        started = perf_counter()
        response = client.get(path, params=params, headers=headers)
        elapsed = perf_counter() - started

        assert response.status_code == 200
        return elapsed, response

    # Simulate 10 concurrent users making 20 requests.
    with ThreadPoolExecutor(max_workers=10) as executor:
        dashboard_results = list(
            executor.map(
                lambda _: measure_request("/api/dashboard"),
                range(20),
            )
        )

        inventory_results = list(
            executor.map(
                lambda page: measure_request(
                    "/api/inventory",
                    {
                        "search": "Load Component",
                        "limit": 100,
                        "offset": page * 100,
                    },
                ),
                range(20),
            )
        )

    for label, results in [
        ("Dashboard", dashboard_results),
        ("Inventory", inventory_results),
    ]:
        times = [elapsed for elapsed, response in results]
        percentage = sum(time <= 3 for time in times) / len(times) * 100

        print(f"{label}: {percentage:.0f}% completed within 3 seconds")

        assert percentage >= 90, (
            f"{label} failed the 3-second performance target"
        )

    assert all(
        len(response.json()) == 100
        for elapsed, response in inventory_results
    )
