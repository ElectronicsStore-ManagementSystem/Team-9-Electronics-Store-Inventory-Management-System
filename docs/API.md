# EIMS API Reference

## 1. Overview

The Electronics Store Inventory Management System exposes HTTP API endpoints through FastAPI.

Interactive API documentation is available at `/docs` while the application is running.

The exact request schemas, response formats, HTTP methods, and authorization requirements should be verified using the interactive API documentation.

## 2. Authentication

### Login

**Endpoint:** `/api/auth/login`

**Purpose:** Authenticate a user and obtain an access token.

The login request uses the application's configured credential fields. On successful authentication, the response includes an access token and user role.

Protected endpoints require authentication according to the application's security configuration.

## 3. Inventory Management

### Inventory Collection

**Endpoint:** `/api/inventory`

**Purpose:** Access the inventory collection and perform supported inventory operations.

Features include:

* Listing inventory components.
* Searching, filtering, and sorting.
* Adding components with validation.
* Generating unique SKUs.

Supported HTTP methods and parameters are documented in `/docs`.

### Individual Inventory Component

**Endpoint:** `/api/inventory/{id}`

**Purpose:** Access or modify an individual component.

Depending on the HTTP method and the user's permissions, supported operations include retrieving, updating, or deleting a component.

### Component Image Upload

**Endpoint:** `/api/inventory/{id}/image`

**Purpose:** Upload an image for an inventory component, subject to the application's validation and authorization rules.

Verify the required multipart form fields and supported file types in `/docs`.

## 4. Dashboard

**Endpoint:** `/api/dashboard`

**Purpose:** Retrieve dashboard information.

The response can include inventory summary information, stock values, low-stock information, recently added components, and other supported dashboard data.

Refer to `/docs` for the exact response schema.

## 5. Branch, Supplier, and Filter Options

### Branch Collection

**Endpoint:** `/api/branches`

Authenticated users can list branches. Admins and managers can add a branch
with `POST /api/branches` using a JSON body containing a required `name`.
Names are trimmed and duplicates are rejected without regard to case. New
components are assigned to `Main Branch` by default for compatibility; select
another branch with the `branch` field when needed. The inventory endpoint
accepts an optional `branch` filter.

### Supplier Collection

**Endpoint:** `/api/suppliers`

Authenticated users can list suppliers. Admins and managers can add a supplier
with `POST /api/suppliers` using a JSON body containing a required `name`.
Names are trimmed and duplicates are rejected. Existing component supplier
values are included so current inventory remains available in filters.

### Category Options

**Endpoint:** `/api/categories`

Authenticated users can retrieve the categories used by active inventory.
New categories appear when components are added.

## 6. Stock Availability Report

**Endpoint:** `/api/reports/availability`

**Purpose:** Retrieve stock availability information for inventory components.

The report concerns inventory quantities and stock classifications, such as:

* In stock.
* Low stock.
* Out of stock.

### Report Export

The frontend supports PDF, Excel, and CSV export actions for the stock availability report.

The export endpoint is:

`/api/reports/availability/export`

The exact supported query parameters and response formats are documented in `/docs`.

## 7. Monthly System Availability Report

**Endpoint:** `/api/reports/system-availability`

**Purpose:** Retrieve system availability information for a specified month and year.

The endpoint accepts `year` and `month` parameters.

The report evaluates recorded monitoring checks, monitoring coverage, downtime incidents, and scheduled maintenance.

Depending on the available data, the response can include:

* The selected year and month.
* Whether monitoring has started.
* Whether monitoring coverage is complete.
* The calculated availability percentage, when sufficient data is available.
* The configured availability target.
* Whether the target was met, when this can be determined.
* A message describing the monitoring or coverage status.

The configured availability target is 99.5%.

When no monitoring checks are available for the selected month, the endpoint returns a response indicating that no monitoring checks were recorded.

When monitoring coverage is incomplete, the response indicates that a definitive availability result cannot be established.

Access is subject to the application's authentication and authorization requirements.

## 8. Error Handling

The API uses HTTP status codes to communicate request outcomes.

Depending on the endpoint and the type of failure, responses may indicate:

* Authentication failure.
* Insufficient permissions.
* Invalid request parameters.
* Invalid request body fields.
* Missing resources.
* Other request or server errors.

Refer to `/docs` for endpoint-specific response details.

## 9. Interactive Documentation

Start the application and open:

`http://127.0.0.1:8000/docs`

If the server uses another port, replace `8000` with the configured port.

The interactive documentation provides the current API operations, parameters, request schemas, and response schemas.
