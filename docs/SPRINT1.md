# Sprint 1 Review Pack

## Project
Electronics Store Inventory Management System (EIMS), Team 9

## Baseline used
The Sprint 1 implementation follows the supplied STP and SAD. The STP calls for unit tests around inventory operations, validation, SKU generation, threshold classification and dashboard calculations, plus integration tests across UI/API/database persistence and authentication/audit behaviour.

## Sprint 1 implemented

| Area | Implementation | Evidence |
|---|---|---|
| Authentication | Login endpoint with signed token | `app/security.py`, `tests/test_integration_api.py` |
| RBAC | Admin/Manager write/delete, Staff read-only | `app/security.py`, integration tests |
| Inventory list | Search, category/supplier/status filters, sort | `app/main.py` |
| Add component | Validation and generated unique SKU | `app/schemas.py`, `app/services.py` |
| Update | Quantity, price, supplier, reorder level | `app/main.py` |
| Delete | Manager/Admin only, soft deletion | `app/main.py` |
| Audit | Delete records user, component, timestamp | `AuditLog`, integration test |
| Availability | Stock classification endpoint | `/api/reports/availability` |
| Dashboard | Count, stock value, low-stock count, recent items | `/api/dashboard` |
| Unit tests | Stock classification, validation, password hashing | `tests/test_unit_*.py` |
| Integration tests | Auth, RBAC, CRUD, audit, report/dashboard | `tests/test_integration_api.py` |
| CI | Build/compile/test on push and PR | `.github/workflows/ci.yml` |

## Requirement mapping

Sprint 1 primarily establishes EIMS-F-001 to EIMS-F-015, EIMS-F-019 and the foundations for EIMS-F-020/F-021. Security foundations cover EIMS-SR-001, SR-003 and SR-006 at application level. Full TLS deployment, 15-minute session enforcement, image upload, exports, real-time alerts, performance/load measurements and operational availability remain follow-up work.

## Demo flow

1. Start the server.
2. Login as `admin`.
3. Show the inventory list and dashboard values.
4. Search/filter inventory.
5. Add a component and show the generated SKU.
6. Delete the new component and show the confirmation plus audit entry through `/api/audit-logs`.
7. Logout and login as `staff`.
8. Show that inventory is readable but add/delete requests return 403.
9. Run `pytest -q`.
10. Push a harmless documentation change and show the GitHub Actions run.

## Sprint 1 not claimed as complete

The supplied STP explicitly leaves several checks for later execution or dependent implementation: 3-second performance validation, 10,000-component/20-user scalability test, production-style TLS verification, 15-minute inactivity expiry, automated injection/XSS scan, full export formats, optional hardware interfaces and monthly availability reporting. These should be scheduled rather than represented as completed without evidence.
