# Sprint 1 API summary

Base URL: `/api`

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | `/auth/login` | Public | Authenticate user |
| GET | `/me` | Authenticated | Current user |
| GET | `/inventory` | Authenticated | List/search/filter/sort components |
| POST | `/inventory` | Admin/Manager | Add component |
| PATCH | `/inventory/{id}` | Admin/Manager | Update stock details |
| DELETE | `/inventory/{id}` | Admin/Manager | Deactivate component and audit |
| GET | `/reports/availability` | Authenticated | Availability classification |
| GET | `/dashboard` | Authenticated | Dashboard summary |
| GET | `/audit-logs` | Admin/Manager | Deletion audit records |
