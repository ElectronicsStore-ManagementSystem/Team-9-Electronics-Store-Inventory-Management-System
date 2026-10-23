# EIMS API reference

The API is served by FastAPI. Interactive request and response schemas are available at `/docs` while the application is running.

## Authentication and roles

Send the login token in the `Authorization` header:

```http
Authorization: Bearer <access_token>
```

`ADMIN` and `MANAGER` can add, update, and delete inventory components. `STAFF` can read inventory and reports but cannot perform those changes. Only `ADMIN` can sort by or see component creation dates. Unauthenticated requests to protected endpoints return `401` with a
`WWW-Authenticate: Bearer` challenge. Invalid or expired tokens also return
`401`; authenticated users without permission receive `403`.

## Endpoints

Base path: `/api`

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | `/auth/login` | Public | Authenticate and return an access token and role |
| GET | `/me` | Authenticated | Return the current user's ID, username, and role |
| GET | `/inventory` | Authenticated | List a page of active components with optional search, filters, and sorting |
| POST | `/inventory` | Admin/Manager | Create a component and assign its unique SKU |
| GET | `/inventory/{component_id}` | Authenticated | Read one active component |
| PATCH | `/inventory/{component_id}` | Admin/Manager | Update quantity, unit price, supplier, or reorder level |
| DELETE | `/inventory/{component_id}` | Admin/Manager | Deactivate a component and record an audit event |
| GET | `/reports/availability` | Authenticated | List active components with stock status |
| GET | `/dashboard` | Authenticated | Return component count, stock value, low-stock count, and recent additions |
| GET | `/audit-logs` | Admin/Manager | Read deletion audit records |

## Inventory list parameters

`GET /api/inventory` supports these optional query parameters:

| Parameter | Behavior |
|---|---|
| `search` | Matches component name, SKU, or category |
| `category` | Exact category filter |
| `supplier` | Exact supplier filter |
| `status` | `in-stock`, `low-stock`, or `out-of-stock` |
| `sort` | `id` (default), `name`, `quantity`, or `unit_price`; prefix with `-` for descending |
| `sort` (ADMIN only) | `date_added` or `date`; prefix with `-` for descending |
| `limit` | Number of records to return, from 1 to 500; defaults to 100 |
| `offset` | Number of matching records to skip; defaults to 0 |

For example, `GET /api/inventory?category=Microcontroller&status=low-stock&sort=-quantity&limit=50&offset=100` returns the third page of low-stock microcontrollers ordered by quantity descending. Pagination and status filtering are applied in the database, so large inventories do not need to be loaded into application memory for each request.

Staff requests to sort by creation date are rejected with `422`.

The frontend highlights low-stock rows with an amber indicator and
`Needs reorder` label. Out-of-stock rows use a separate red indicator. The
highlight is recalculated whenever inventory is refreshed, including after a
quantity or reorder-level update.

The dashboard displays total component count, total stock value, low-stock
count, and a clickable list of the five most recently added active components.

## Component payloads

Component creation requires `name`, `category`, `quantity`, `unit_price`, and `supplier`. `reorder_level` is optional and defaults to `5`; `image_url` is optional. Text fields are trimmed and cannot be blank. Quantity, unit price, and reorder level must be nonnegative; unit price must be finite.

Creation returns `201 Created` with the assigned `id` and unique `sku`. Invalid payloads return `422`. Update payloads may include any subset of `quantity`, `unit_price`, `supplier`, and `reorder_level`.

The `created_at` field is returned to admins. It is `null` for other roles in component, dashboard, and availability responses.

## Error behavior

Errors use FastAPI's standard JSON error response with a `detail` field. Common statuses include `401` for unauthenticated requests, `403` for insufficient permissions, `404` for missing or inactive components, `409` for conflicting identifiers, and `422` for invalid input or unsupported sort values.
