import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Log in using the test admin credentials
response = client.post(
    "/api/auth/login",
    json={"username": "admin", "password": "Admin@12345"},
)

print("Login status:", response.status_code)

if response.status_code != 200:
    print("Login failed:", response.text)
    raise SystemExit(1)

token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Warm-up request
client.get("/api/inventory?search=Arduino", headers=headers)

# Measure 10 search requests
times = []

for _ in range(10):
    start = time.perf_counter()
    response = client.get(
        "/api/inventory?search=Arduino",
        headers=headers,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000
    times.append(elapsed_ms)

    if response.status_code != 200:
        print("Search failed:", response.status_code, response.text)
        raise SystemExit(1)

print("Search status:", response.status_code)
print("Times (ms):", [round(t, 2) for t in times])
print("Average (ms):", round(sum(times) / len(times), 2))
print("Maximum (ms):", round(max(times), 2))
print("All requests under 2 seconds:", max(times) < 2000)