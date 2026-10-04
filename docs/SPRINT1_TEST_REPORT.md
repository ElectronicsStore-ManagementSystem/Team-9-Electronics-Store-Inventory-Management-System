# Sprint 1 Test Report

## Test Execution Summary

- Test command: `python -m pytest -q`
- Result: **18 passed, 1 warning**
- Failed tests: **0**
- `git diff --check`: **Passed**

## Unit Tests

| Test Area | Result |
|---|---|
| Inventory validation | PASS |
| Stock classification | PASS |
| SKU generation | PASS |
| Password hashing | PASS |
| Password verification | PASS |
| Search input validation | PASS |

## Integration Tests

| Test Case | Result |
|---|---|
| Unauthenticated inventory request returns 401 | PASS |
| Staff can read inventory | PASS |
| Staff cannot add/delete components | PASS |
| Admin can add, update and delete components | PASS |
| Delete operation creates audit record | PASS |
| Duplicate component creation generates unique SKUs | PASS |
| Availability report | PASS |
| Dashboard summary | PASS |

## Security Validation

| Requirement | Result |
|---|---|
| Authentication | PASS |
| Role-based access control | PASS |
| Protected inventory routes | PASS |
| Password hashing and verification | PASS |
| Input/schema validation | PASS |
| Audit access restricted to Admin/Manager | PASS |

## CI

GitHub Actions workflow is configured in:

`.github/workflows/ci.yml`

The workflow installs the project requirements and runs the pytest suite on push.

## Not Claimed as Completed

The following validations were not executed and therefore are not marked as passed:

- Production-style TLS verification
- 15-minute inactivity session enforcement
- 3-second performance validation
- 10,000-component / 20-user scalability test
- Automated injection/XSS scan
- Full export formats
- Real-time alerts
- Monthly availability reporting

These remain follow-up work.