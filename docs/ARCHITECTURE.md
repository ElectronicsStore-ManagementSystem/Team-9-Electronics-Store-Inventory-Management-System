# Architecture and module responsibilities

EIMS is organized as a small layered application. The running application uses the `frontend/` directory and the Python package under `app/`.

## Layers

| Layer | Location | Responsibility |
|---|---|---|
| UI | `frontend/index.html`, `frontend/style.css`, `frontend/app.js` | Render the inventory interface, collect input, call HTTP endpoints, and display results and errors. It contains no database queries. |
| API | `app/main.py` | Define FastAPI routes, parse requests, enforce authentication/authorization dependencies, select response shapes, and translate failures into HTTP responses. |
| Business rules | `app/services.py`, `app/security.py`, `app/schemas.py` | Classify stock, normalize search text, validate request data, authenticate users, and enforce role requirements. |
| Data access | `app/repositories.py`, `app/db.py`, `app/models.py` | Execute SQLAlchemy queries and mutations, manage database sessions, and define persistence models. |
| Application setup | `app/bootstrap.py`, `app/config.py` | Initialize database tables and development seed data, and load environment-based configuration. |

## Request flow

```text
Browser
  frontend/app.js
      │ HTTP request / JSON response
      ▼
FastAPI routes
  app/main.py
      ├── validation, auth, and stock rules
      │   app/schemas.py / app/security.py / app/services.py
      ▼
SQLAlchemy repositories
  app/repositories.py
      ▼
Session and mapped entities
  app/db.py / app/models.py
      ▼
SQLite (development default; URL configurable)
```

For example, a component update is validated by the request schema, authorized by the API's manager dependency, persisted by `repositories.update_component`, and returned by the API for the UI to render. The UI refreshes the inventory only after a successful response.

## Module guide

- `app/main.py` is the application entry point and API composition module. Run it with `uvicorn app.main:app`.
- `app/repositories.py` is the boundary for application SQL queries and persistence mutations. Keep route handlers free of SQLAlchemy query construction.
- `app/db.py` owns engine/session configuration and the request-scoped session dependency.
- `app/models.py` defines the SQLAlchemy tables; `app/schemas.py` defines validated API payloads and responses.
- `app/bootstrap.py` creates mapped tables and seeds development demo records.
- `app/services.py` holds small inventory business rules that do not perform database access.
- `app/security.py` owns password hashing/token handling and reusable role dependencies. Passwords are stored as PBKDF2-HMAC-SHA256 digests with per-password random salts; login verifies hashes only and does not fall back to plaintext comparison.
- `backend/` contains earlier standalone domain/service prototypes, some retained for isolated unit tests. It is not imported by the running FastAPI application; application endpoints use `app/`.
- `tests/` contains API integration tests and isolated unit tests.
- `docs/API.md` documents HTTP endpoints, roles, parameters, payloads, and error behavior.

## Dependency direction

The frontend depends on the API's HTTP contract, not Python modules or persistence details. API routes depend on schemas, security/business rules, and repository interfaces. Repositories depend on SQLAlchemy sessions and models. Database/model code does not import API routes or frontend assets.

This separation keeps HTTP behavior and UI rendering independent of query implementation, and makes route and repository behavior testable without coupling them to the browser.
