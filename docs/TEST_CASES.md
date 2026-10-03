# Sprint 1 Test Cases

| ID | Type | Requirement | Scenario | Expected |
|---|---|---|---|---|
| TC-Inv-01 | Integration | F-001 | Authenticated user lists inventory | Active inventory is returned with required fields |
| TC-Inv-02 | Integration | F-002 | Search by name/SKU/category | Matching rows are returned |
| TC-Inv-03 | Integration | F-003 | Filter by stock status | Only matching status is returned |
| TC-Inv-04 | Integration | F-004 | Sort inventory | Requested ordering is applied |
| TC-Inv-05 | Integration | F-005 | Manager updates quantity | Change persists |
| TC-Add-01 | Integration | F-006 | Add valid component | Component is created |
| TC-Add-02 | Unit/Integration | F-007 | Add multiple components | SKUs are unique and non-reused in normal flow |
| TC-Add-03 | Unit/Integration | F-008 | Missing/negative data | Validation rejects invalid data |
| TC-Add-04 | Integration | F-009 | Create repeated payload | Each new component gets a different SKU |
| TC-Del-01 | Integration | F-011 | Manager deletes component | Component becomes inactive |
| TC-Del-03 | Security | F-013 / SR-003 | Staff calls delete | HTTP 403 |
| TC-Del-04 | Integration | F-014 | Verify deletion audit | User, component and timestamp are recorded |
| TC-Rep-01 | Integration | F-015 | Availability report | In/low/out statuses are classified correctly |
| TC-Dash-01 | Integration | F-019 | Dashboard summary | Count/value/low-stock data is correct |
| TC-Sec-01 | Security | SR-001 | Unauthenticated inventory request | HTTP 401 |
| TC-Sec-03 | Security | SR-003 | Staff invokes manager endpoint | HTTP 403 |
| TC-Sec-06 | Unit/Integration | SR-006 | Malformed values | Schema validation rejects invalid input |
