# Electronics Store Inventory Management System (EIMS)

**Team 9 | Electronics Store Inventory Management System**

## Team Members 

1. Krishitha Kanakala ---PES2UG24CS234
2. Jayashree D        --PES2UG24CS203
3. Hemavathi E        --PES2UG24CS193
4. Karan Maheshwari   --PES2UG24CS216

<h4>Jira Scrum Board: https://kristak.atlassian.net/jira/software/projects/T9ESIMS/summary</h4>


EIMS is a web-based inventory management system designed for an electronics store. It provides inventory management, authentication, role-based access control, stock availability reporting, dashboard summaries, input validation, and automated testing.

The application also includes monthly system availability reporting based on monitoring checks, downtime incidents, and scheduled maintenance.

## Project Scope and Features

### 1. Authentication and Role-Based Access Control

* User authentication before accessing protected inventory functions.
* Role-based access control for Admin, Manager, and Staff users.
* Restricted inventory operations according to user permissions.
* Session handling using authentication tokens.

### 2. Inventory Management

* List and view inventory components.
* Search components by supported fields.
* Filter inventory by category, supplier, and stock status.
* Sort inventory using supported fields and sort orders.
* Add new components with input validation.
* Generate unique SKUs for inventory components.
* Update component quantity, unit price, supplier, and reorder level.
* Delete components with appropriate authorization and UI confirmation.
* Classify inventory stock into:

  * In stock
  * Low stock
  * Out of stock

### 3. Dashboard and Inventory Insights

* Display inventory summary information.
* Show total component count and total stock value.
* Display low-stock information.
* Provide recently added component information.
* Visualize inventory summaries and trends where supported by available data.

### 4. Stock Availability Reporting

The stock availability report provides information about the current inventory status of active components.

The report API is:

`/api/reports/availability`

The report supports inventory availability information, including component quantities and stock classifications.

Integration tests cover stock classifications, updated inventory values, and the exclusion of inactive components.

Supported report export formats include PDF, Excel, and CSV where available in the application.

### 5. Monthly System Availability Reporting

The monthly system availability feature provides a report for a selected month and year using recorded monitoring data.

The report API is:

`/api/reports/system-availability`

The report evaluates:

* Recorded system availability checks.
* Monitoring coverage for the selected month.
* Downtime incidents.
* Scheduled maintenance periods.
* Calculated availability percentage when sufficient monitoring data is available.
* Comparison against the configured availability target of 99.5%.

When monitoring data is unavailable, the endpoint returns a response indicating that no monitoring checks were recorded for the selected month.

When monitoring coverage is incomplete, the report indicates that a definitive availability result cannot be established from the available data.

Scheduled maintenance is handled separately from unplanned downtime when calculating availability.

Access to this report is restricted according to the application's authentication and authorization rules.

### 6. Validation and Error Handling

* Validate required component fields.
* Validate numeric values such as quantity, unit price, and reorder level.
* Provide appropriate error responses for invalid input.
* Display validation feedback in the frontend.
* Handle unsuccessful API requests and authentication failures.

### 7. Security and Auditability

* Authentication for protected API endpoints.
* Role-based authorization for restricted operations.
* Input validation and error handling.
* HTTPS enforcement by default, with a separate HTTPS launcher for TLS deployments.
* Audit logging for supported operations.

### 8. Automated Testing and Continuous Integration

* Unit tests for supported business logic.
* Integration tests for API endpoints.
* Tests for authentication and authorization.
* Tests for inventory operations and validation.
* Tests for stock availability reporting.
* Integration tests for monthly system availability reporting.
* GitHub Actions CI pipeline, if configured in the repository.

The project uses automated tests to verify application behavior and help prevent regressions as new features are introduced.

## Technology Stack

* **Language:** Python
* **Backend framework:** FastAPI
* **ORM:** SQLAlchemy
* **Development database:** SQLite
* **Testing framework:** Pytest
* **Frontend:** HTML, CSS, and JavaScript
* **API documentation:** FastAPI Swagger UI
* **Version control:** Git and GitHub
* **Continuous integration:** GitHub Actions, if configured

The application separates frontend functionality, HTTP API endpoints, business logic, and persistence operations.

For additional details, see:

* [Architecture and module responsibilities](docs/ARCHITECTURE.md)
* [API reference](docs/API.md)

## Prerequisites

Before running the application, install:

* Python 3.12 or a compatible version supported by the project's dependencies.
* Git, if cloning the repository.
* PowerShell on Windows, or a compatible terminal on macOS/Linux.

Install the dependencies listed in `requirements.txt` before starting the application.

## Run Locally

### Windows PowerShell

Create a virtual environment, activate it, install dependencies, and start the application:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:EIMS_ENFORCE_HTTPS = "false"
python -m uvicorn app.main:app --reload
```

If PowerShell blocks virtual environment activation, review your local execution policy and use an appropriate activation method for your environment.

### macOS/Linux

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
EIMS_ENFORCE_HTTPS=false python -m uvicorn app.main:app --reload
```

### Access the application

By default, the development server is available at:

`http://127.0.0.1:8000`

API documentation is available at:

`http://127.0.0.1:8000/docs`

Use the port configured for your server if you start Uvicorn with a different port.

## HTTPS and TLS Configuration

The application redirects HTTP requests to HTTPS by default.

For local development, HTTPS enforcement can be disabled using:

```powershell
$env:EIMS_ENFORCE_HTTPS = "false"
```

For HTTPS/TLS deployments, provide a certificate and private key and start the dedicated TLS launcher.

### Windows PowerShell

```powershell
$env:EIMS_TLS_CERTFILE = "C:\path\to\certificate.pem"
$env:EIMS_TLS_KEYFILE = "C:\path\to\private-key.pem"
python run_https.py
```

### Deployment considerations

* Configure a valid TLS certificate and private key.
* Use TLS 1.2 or later.
* When deploying behind a reverse proxy, configure the proxy to redirect HTTP requests to HTTPS.
* Configure the proxy to forward only HTTPS traffic to the application.
* Keep private keys and production secrets outside version control.
* Use secure, deployment-specific credentials rather than development demo credentials.

## Demo Accounts

The application may create demo accounts during initial startup or database initialization, depending on the configured initialization process.

The documented development credentials are:

| Role  | Username | Password      |
| ----- | -------- | ------------- |
| Admin | `admin`  | `Admin@12345` |
| Staff | `staff`  | `Staff@12345` |

These credentials are for development and testing only. Verify that they are configured in your local environment before using them.

**Do not use demo credentials in a production deployment.** Configure secure credentials before deploying the application.

## API Endpoints

The following endpoints represent the principal documented API capabilities. Check the API documentation at `/docs` for the current request parameters, response schemas, and authorization requirements.

| Endpoint                           | Purpose                                                                     |
| ---------------------------------- | --------------------------------------------------------------------------- |
| `/api/auth/login`                  | Authenticate a user and obtain an access token.                             |
| `/api/inventory`                   | Access the inventory collection and supported inventory operations.         |
| `/api/inventory/{id}`              | Access or modify an individual inventory component, subject to permissions. |
| `/api/dashboard`                   | Retrieve dashboard summary information.                                     |
| `/api/reports/availability`        | Retrieve the stock availability report.                                     |
| `/api/reports/system-availability` | Retrieve monthly system availability information using monitoring data.     |

The available HTTP methods and authorization requirements depend on the specific endpoint.

## Run Tests

Activate the project's virtual environment and run the complete test suite from the repository root:

```bash
pytest -q
```

### Run Monthly System Availability Tests

```bash
pytest -q tests/integration/test_system_availability.py
```

These tests cover authentication, authorization, invalid date parameters, missing monitoring data, availability calculations, scheduled maintenance handling, and incomplete monitoring coverage.

### Run Scalability Tests

The scalability regression test can be executed separately:

```bash
pytest -q tests/test_scalability.py
```

The test is intended to exercise inventory handling with a large dataset and concurrent paginated requests.

Test results may vary as new tests and features are added. Run the current test suite to obtain the latest results.

## Project Architecture

The application is organized into components responsible for:

* Frontend user interaction.
* HTTP API routes and request handling.
* Authentication and authorization.
* Inventory and reporting business logic.
* Database models and persistence.
* Unit and integration testing.

For the current module structure and request flow, refer to [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

For endpoint details, refer to [docs/API.md](docs/API.md) and the interactive API documentation at `/docs`.

## Sprint and Git Workflow

The `main` branch is the integration branch. Team members should work on separate feature branches and open pull requests for review.

Do not commit directly to `main`.

### Example Branch Names

```text
feature/karan-auth-api
feature/krishitha-inventory-api
test/jayashree-integration-tests
qa/hemavathi-ci-security
feature/issue-22-system-availability
```

Use descriptive branch names that match the assigned task or issue.

### Commit Message Examples

```text
feat(auth): add login and role middleware
feat(inventory): add component CRUD endpoints
feat(inventory): generate unique SKUs
test(inventory): add CRUD integration coverage
test(reports): cover monthly system availability
fix(frontend): correct initialization order for login
ci: add GitHub Actions test pipeline
docs: update project README
```

Each team member should configure their own Git name and email and commit their own contributions. Do not fabricate author identity in commits.

### Pull Request Workflow

1. Create a feature branch from the appropriate base branch.
2. Implement the assigned changes.
3. Run relevant tests locally.
4. Review the changes before committing.
5. Push the feature branch to GitHub.
6. Open a pull request targeting `main`.
7. Describe the changes and testing performed.
8. Resolve review feedback and merge according to the team's workflow.

Keep pull requests focused on the assigned issue or feature whenever possible.

## Future Improvements

Potential improvements depend on the project roadmap and the features approved for subsequent sprints. These may include:

* Expanded reporting and export capabilities.
* Additional dashboard analytics.
* More comprehensive monitoring and availability tracking.
* Further security hardening.
* Additional automated tests.
* Performance and scalability improvements.

Only mark a feature as completed once its implementation and behavior have been verified.

## Team

**Team 9 — Electronics Store Inventory Management System**

This project is developed collaboratively by the team as part of the academic software engineering project.
