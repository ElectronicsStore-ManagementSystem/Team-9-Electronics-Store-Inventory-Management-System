# EIMS Architecture and Module Responsibilities

## 1. Overview

The Electronics Store Inventory Management System (EIMS) is a web-based application for managing electronic components, controlling user access, and generating inventory and system availability reports.

The application consists of a frontend, a FastAPI backend, business logic, and database persistence.

## 2. High-Level Architecture

```text
User
 |
 v
Frontend (HTML, CSS, JavaScript)
 |
 v
FastAPI Application
 |
 +-- Authentication and Authorization
 |
 +-- Inventory Management
 |
 +-- Stock Movement Management
 |
 +-- Branch and Supplier Management
 |
 +-- Purchase Order Management
 |
 +-- Dashboard
 |
 +-- Reporting and Monitoring
 |
 v
SQLAlchemy ORM
 |
 v
SQLite Development Database
```

## 3. Frontend

The frontend provides the user interface for interacting with the application.

Responsibilities include:

- Login and logout.
- Displaying inventory components.
- Searching, filtering, and sorting inventory.
- Adding and updating components.
- Managing suppliers and loading category, supplier, and branch filter options.
- Managing shop branches.
- Recording and viewing stock movement history.
- Creating and managing purchase orders.
- Displaying stock classifications.
- Showing dashboard information.
- Switching between persistent light and dark themes.
- Displaying reports and handling supported exports.
- Displaying validation messages and API errors.

The frontend uses HTML, CSS, and JavaScript.

## 4. Backend

The backend uses FastAPI to expose HTTP endpoints and process requests.

Responsibilities include:

- Processing API requests.
- Validating request parameters and request bodies.
- Enforcing authentication and authorization.
- Managing inventory operations.
- Generating unique SKUs.
- Managing the supplier catalog and shop branches.
- Providing dynamic category, supplier, and branch filter options.
- Recording stock movements and maintaining movement history.
- Managing purchase orders, order status, and stock receipts.
- Providing dashboard information.
- Generating stock availability reports.
- Calculating monthly system availability from monitoring records.
- Returning appropriate HTTP responses.

## 5. Authentication and Authorization

Authentication verifies user credentials and provides an access token.

Protected endpoints use the application's authentication and authorization mechanisms to restrict access according to user roles.

The application supports Admin, Manager, and Staff roles. Permissions depend on the specific operation and endpoint.

## 6. Inventory Management

Inventory functionality includes:

- Listing and retrieving components.
- Searching, filtering, and sorting.
- Adding components with validation.
- Generating unique SKUs.
- Updating supported component fields.
- Deleting components subject to authorization.
- Assigning components to shop branches.
- Classifying stock based on quantity and reorder level.

### Stock Movement Management

Stock movement functionality records stock-in and stock-out operations.

It includes:

- Recording movement types and quantities.
- Capturing movement reasons.
- Recording timestamps and responsible user information.
- Maintaining component movement history.
- Updating inventory quantities through recorded movements.

### Branch and Supplier Management

Branch management supports creating and retrieving shop branches and assigning inventory components to branches.

Supplier management maintains supplier information and provides supplier options for inventory filters and purchase orders.

### Purchase Order Management

Purchase order functionality includes:

- Creating purchase orders for suppliers.
- Adding components and quantities to orders.
- Viewing purchase orders and their details.
- Updating editable order statuses.
- Recording full and partial stock deliveries.
- Maintaining receipt history.
- Preventing duplicate receipt processing through idempotency keys.

## 7. Reporting and Monitoring

### Stock Availability

The stock availability report provides information about component quantities and stock classifications.

### Monthly System Availability

The monthly system availability report uses monitoring checks, downtime incidents, and scheduled maintenance records to calculate availability for a selected month.

The report considers monitoring coverage when determining whether a definitive availability result can be reported.

## 8. Persistence Layer

SQLAlchemy provides the application's ORM layer for database operations.

SQLite is used as the development database. Database models represent application entities such as inventory components, users, branches, suppliers, purchase orders, stock movements, and monitoring records.

## 9. Testing

Pytest is used for automated testing.

Tests cover supported business logic, API behavior, authentication, authorization, inventory operations, validation, stock movements, purchase orders, branch management, and reporting.

## 10. Request Flow

A typical request follows these steps:

1. The user performs an action in the frontend.
2. JavaScript sends an HTTP request to the FastAPI backend.
3. The backend validates the request.
4. Authentication and authorization checks are performed where required.
5. The application executes the relevant business logic.
6. SQLAlchemy accesses the database when needed.
7. The backend returns a response.
8. The frontend displays the result or an appropriate error message.