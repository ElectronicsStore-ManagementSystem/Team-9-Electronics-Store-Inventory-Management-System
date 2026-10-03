# Electronics Store Inventory Management System (EIMS)

Team 9 | Sprint 1

EIMS is a web-based inventory management system for an electronics store. Sprint 1 establishes the working backend, core inventory workflow, authentication and role-based access control, audit logging, automated tests, and CI.

## Sprint 1 scope

Aligned with the supplied STP/SAD baseline:

- Authentication before protected inventory functions
- Admin/Manager and Staff roles
- Inventory listing, search, filter and sort
- Add component with validation and unique SKU generation
- Update quantity, price, supplier and reorder level
- Delete component for Admin/Manager with confirmation handled by the UI and an audit record in the API
- Availability classification: in-stock, low-stock and out-of-stock
- Dashboard summary endpoint
- Unit and integration tests
- GitHub Actions build/test pipeline

The supplied project baseline also specifies reporting, exports, charts, low-stock alerts, responsive UI, security hardening and scalability. Those are tracked for subsequent sprints rather than being falsely marked complete in Sprint 1.

## Stack

- Python 3.12+
- FastAPI
- SQLAlchemy + SQLite for the Sprint 1 development database
- Pytest
- Vanilla HTML/CSS/JavaScript frontend served by FastAPI
- GitHub Actions

The architecture keeps the API/data layers separate so the development database can be replaced later without changing the public API contract.

## Run locally

```bash
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

Demo accounts are created automatically on first startup:

- `admin / Admin@12345`
- `staff / Staff@12345`

These are development-only credentials. Change them before any deployment.

API documentation is available at `/docs`.

## Run tests

```bash
pytest -q
```

## Sprint 1 Git workflow

`main` is the integration branch. Each member works on a short-lived branch and opens a pull request. Do not commit directly to `main`.

Recommended branches:

- `feature/karan-auth-api`
- `feature/krishitha-inventory-api`
- `test/jayashree-integration-tests`
- `qa/hemavathi-ci-security`

Use focused commits such as:

```text
feat(auth): add login and role middleware
feat(inventory): add component CRUD endpoints
test(inventory): add CRUD integration coverage
ci: add GitHub Actions test pipeline
docs(sprint1): add review and contribution guide
```

Do not fabricate author identity in commits. Each team member should configure their own Git name/email and commit their own contribution.
