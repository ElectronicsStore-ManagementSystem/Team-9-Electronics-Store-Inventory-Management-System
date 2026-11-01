# Electronics Store Inventory Management System (EIMS)

**Team 9 | Software Engineering Project | PES University**

**Application Version:** `1.1.0`

EIMS is a web-based Electronics Store Inventory Management System developed to simplify and streamline inventory operations for an electronics retail business. The application provides centralized inventory management, supplier and branch management, purchase order processing, stock movement tracking, reporting, authentication, and role-based access control.

The system is built using **FastAPI, SQLAlchemy, SQLite, HTML, CSS, and JavaScript**, with automated testing through Pytest and continuous integration through GitHub Actions.

---

## 1. Team Members

| No. | Team Member | University ID | GitHub |
|---|---|---|---|
| 1 | Krishitha Kankanala | PES2UG24CS234 | [@krista9669](https://github.com/krista9669) |
| 2 | Jayashree D | PES2UG24CS203 | [@Jayashree-D-CSE](https://github.com/Jayashree-D-CSE) |
| 3 | Hemavathi E | PES2UG24CS193 | [@Hema3156](https://github.com/Hema3156) |
| 4 | Karan Maheshwari | PES2UG24CS216 | [@Progamer24](https://github.com/Progamer24) |

---

## 2. Project Objectives

The primary objectives of EIMS are to:

- Digitize electronics store inventory operations.
- Maintain accurate component and stock information.
- Manage suppliers, branches, and purchase orders.
- Track stock additions and deductions.
- Provide inventory insights through dashboards and reports.
- Enforce secure authentication and role-based access.
- Improve operational visibility through audit logging and system availability monitoring.
- Maintain software quality through automated testing and continuous integration.

---

## 3. Features and Functionalities

### 3.1 Authentication and Role-Based Access Control

- User authentication for protected application functionality.
- Role-based permissions for Admin, Manager, and Staff users.
- Restricted inventory operations according to assigned permissions.
- Token-based authentication and session handling.
- Authorization checks for protected API endpoints.

### 3.2 Inventory Management

- Create, view, update, and delete inventory components.
- Search components using supported fields.
- Filter inventory by category, supplier, branch, and stock status.
- Sort inventory using supported fields and sort orders.
- Generate unique SKUs for inventory components.
- Update unit prices, supplier details, branch assignments, and reorder levels.
- Validate inventory fields and numeric inputs.
- Classify stock into:
  - In Stock
  - Low Stock
  - Out of Stock

### 3.3 Supplier and Branch Management

- Add and manage suppliers.
- Maintain supplier information for inventory components.
- Manage store branches.
- Assign inventory components to branches.
- Reuse supplier and branch information across component forms and inventory filters.

### 3.4 Stock Movement Management

- Record stock-in and stock-out operations.
- Require positive movement quantities and reasons.
- Automatically update inventory quantities.
- Maintain stock movement history for individual components.
- Display movement type, quantity, reason, date, time, and responsible user's role.
- Provide a responsive stock movement history interface.

### 3.5 Purchase Order Management

- Create purchase orders for suppliers.
- Track purchase order status.
- Support partial and complete order receiving.
- Record received quantities.
- Update inventory based on received stock.
- Maintain purchase order information for inventory operations.

### 3.6 Component Image Management

- Upload component images in PNG, JPEG, and WebP formats.
- Enforce a maximum upload size of 5 MB.
- Replace or remove existing component images.
- Store image files in `uploads/components/`.
- Persist image references with component records.

Uploaded images are runtime data and are excluded from Git. Persistent storage and appropriate backups are required for deployments.

### 3.7 Dashboard and Inventory Insights

- Display inventory summary information.
- Show total component count and total stock value.
- Display low-stock information.
- Show recently added components.
- Visualize inventory summaries and trends where supported.
- Support persistent light and dark theme preferences.

### 3.8 Stock Availability Reporting

The stock availability report provides information about the current inventory status of active components.

**API endpoint:**

`GET /api/reports/availability`

The report includes:
- Component quantities.
- Stock classifications.
- Current inventory availability information.
- Exclusion of inactive components.

Supported export formats include PDF, Excel, and CSV where available in the application.

### 3.9 Monthly System Availability Reporting

The monthly system availability feature provides a report for a selected month and year using recorded monitoring information.

**API endpoint:**

`GET /api/reports/system-availability`

The report considers:
- Recorded system availability checks.
- Monitoring coverage.
- Downtime incidents.
- Scheduled maintenance periods.
- Calculated availability percentage when sufficient data is available.
- Comparison against the configured availability target of 99.5%.

Incomplete or unavailable monitoring data is handled explicitly rather than presenting an unsupported availability result.

### 3.10 Validation, Security, and Auditability

- Required-field and numeric input validation.
- Structured API error responses.
- Authentication and authorization for protected operations.
- Role-based restrictions.
- HTTPS enforcement and TLS configuration support.
- Audit logging for supported operations.
- Security-focused automated tests.

---

## 4. Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Backend Framework | FastAPI |
| ORM | SQLAlchemy |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript |
| Testing Framework | Pytest |
| Coverage Measurement | pytest-cov |
| Test Reporting | pytest-html |
| API Documentation | FastAPI Swagger UI |
| Version Control | Git, GitHub |
| Continuous Integration | GitHub Actions |

### Application Architecture

The application is organized into logical components:

1. **Presentation Layer** – HTML, CSS, and JavaScript frontend.
2. **Application Layer** – FastAPI routes and request handling.
3. **Security Layer** – Authentication and authorization.
4. **Business Logic Layer** – Inventory, suppliers, branches, stock movements, purchase orders, and reporting.
5. **Data Access Layer** – SQLAlchemy models and repository operations.
6. **Persistence Layer** – SQLite database and component image storage.

### API Error Handling

API errors use a consistent JSON structure across inventory, authentication, and
reporting endpoints:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": []
  },
  "detail": []
}
```

The `error.code` identifies the failure category, while `error.message` is safe
for display to clients. Validation details identify the invalid request fields.
Unexpected server errors return a generic message without exposing implementation
details or stack traces.

For additional architectural details, refer to the [Architecture Documentation](docs/ARCHITECTURE.md).

---

## 5. Project Documentation

The project documentation is maintained in the `docs/` directory.

### 5.1 Software Engineering Documents

| Document | Description |
|---|---|
| [Software Requirements Specification (SRS)](docs/9_SRS_updated.pdf) | Functional and non-functional requirements, constraints, and acceptance criteria |
| [Software Architecture Document (SAD)](docs/9_SAD_updated.pdf) | Application architecture, components, workflows, and design decisions |
| [Software Test Plan](docs/9_TestPlan_updated.pdf) | Testing strategy, test cases, and requirements traceability |
| [UML Component Diagram](docs/UML_diagram.png) | Visual representation of the application's component architecture |
| [Architecture Documentation](docs/ARCHITECTURE.md) | Module responsibilities and application structure |
| [API Documentation](docs/API.md) | API endpoints, request handling, and response details |

### 5.2 Testing and Quality Assurance Reports

The following reports document the execution and quality measurements of the application.

| Report | Description |
|---|---|
| [Unit Testing Report](docs/reports/9_Unit_Testing_Report.pdf) | Unit test cases and execution results |
| [System Validation Report](docs/reports/9_System_Validation_Report.pdf) | Integration, security, scalability, and system validation results |
| [Code Coverage Report](docs/reports/9_Code_Coverage_Report.pdf) | Statement and line coverage measurements |
| [Branch Coverage Report](docs/reports/9_Branch_Coverage_Report.pdf) | Branch-aware coverage measurements |

---

## 6. Testing and Quality Assurance

EIMS uses automated unit, integration, security, and system-level tests to verify application functionality.

### 6.1 Test Execution Results

The complete project test suite was executed using Pytest.

| Metric | Result |
|---|---:|
| Total tests executed | 181 |
| Passed | 181 |
| Failed | 0 |
| Overall test pass rate | 100% |
| Execution environment | Python 3.12.7 |
| Testing framework | Pytest 8.3.5 |

### 6.2 Unit Testing

Selected unit test modules cover:

- Dashboard summary functionality.
- Inventory validation.
- Stock classification.
- Unique SKU generation.
- Stock value calculations.
- Search input handling.
- Password hashing and verification.
- Password security validation.

**Recorded result:** 13 tests passed.

### 6.3 System Validation

System validation covers integrated application functionality, including:

- Authentication and authorization.
- Branch management.
- Component image management.
- Purchase order processing.
- Stock movement management.
- Supplier management.
- Reporting APIs.
- System availability reporting.
- Security and role permissions.
- Scalability and transport security checks.

**Recorded result:** 98 tests passed.

### 6.4 Code Coverage

Line coverage was measured using `pytest-cov`.

| Metric | Result |
|---|---:|
| Statements | 1,139 |
| Missed statements | 172 |
| Line coverage | **85%** |

### 6.5 Branch Coverage

Branch-aware coverage was measured using the coverage tool with branch measurement enabled.

| Metric | Result |
|---|---:|
| Branch opportunities | 250 |
| Partially covered branch points | 53 |
| Combined statement-and-branch coverage | **83%** |

The 83% value represents combined coverage reported by the tool, not a separately calculated branch-only percentage.

### 6.6 Continuous Integration

The project uses GitHub Actions to execute automated tests when changes are pushed to the repository.

The CI workflow installs project dependencies and executes the Pytest test suite.

**Latest recorded CI status:** Successful.

[View GitHub Actions](https://github.com/ElectronicsStore-ManagementSystem/Team-9-Electronics-Store-Inventory-Management-System/actions)

---

## 7. Installation and Setup

### Prerequisites

- Python 3.12 or a compatible version supported by the project dependencies.
- Git.
- PowerShell on Windows or a compatible terminal on macOS/Linux.

### Clone the Repository

```bash
git clone https://github.com/ElectronicsStore-ManagementSystem/Team-9-Electronics-Store-Inventory-Management-System.git

cd Team-9-Electronics-Store-Inventory-Management-System
```

### Create a Virtual Environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux**

```bash
python -m venv .venv
source .venv/bin/activate
```

### Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### Start the Application

```bash
python run_local.py
```

### Access the Application

| Resource | Address |
|---|---|
| Local Application | http://127.0.0.1:8000 |
| Interactive API Documentation | http://127.0.0.1:8000/docs |

The local development launcher uses port `8000` and binds to the local machine.

---

## 8. HTTPS and TLS Configuration

The application supports HTTPS enforcement and a dedicated TLS launcher.

For local development, HTTPS enforcement can be disabled using:

```powershell
$env:EIMS_ENFORCE_HTTPS = "false"
```

For TLS deployment, configure a certificate and private key.

**Windows PowerShell:**

```powershell
$env:EIMS_TLS_CERTFILE = "C:\path\to\certificate.pem"
$env:EIMS_TLS_KEYFILE = "C:\path\to\private-key.pem"

python run_https.py
```

### Deployment Considerations

- Configure a valid TLS certificate and private key.
- Use TLS 1.2 or later.
- Keep production credentials and private keys outside version control.
- Use secure, deployment-specific credentials.
- Configure persistent storage for uploaded component images.
- Configure HTTPS redirection appropriately when using a reverse proxy.

---

## 9. API Endpoints

The following table lists the principal documented API capabilities.

| Endpoint | Purpose |
|---|---|
| `/api/auth/login` | Authenticate users and obtain an access token |
| `/api/inventory` | Access and manage inventory collections |
| `/api/inventory/{id}` | Access or modify an individual component |
| `/api/inventory/{id}/movements` | Record or view stock movement history |
| `/api/dashboard` | Retrieve dashboard summaries |
| `/api/purchase-orders` | Create and manage purchase orders |
| `/api/reports/availability` | Retrieve stock availability information |
| `/api/reports/system-availability` | Retrieve monthly system availability information |

For the complete endpoint specifications, request schemas, response formats, and authorization requirements, refer to the [API documentation](docs/API.md) or the interactive Swagger UI.

---

## 10. Running Tests

Activate the virtual environment and run the complete test suite:

```bash
pytest -q
```

### Run Unit Tests

```bash
pytest tests/unit tests/test_unit_services.py tests/test_unit_security.py -v
```

### Run Integration Tests

```bash
pytest tests/integration -v
```

### Run Security Tests

```bash
pytest tests/security -v
```

### Run System Availability Tests

```bash
pytest -q tests/integration/test_system_availability.py
```

### Run Scalability Tests

```bash
pytest -q tests/test_scalability.py
```

### Generate Code Coverage

```bash
pytest --cov=app --cov-report=term-missing --cov-report=html:htmlcov --cov-report=xml:coverage.xml
```

### Generate Branch-Aware Coverage

```bash
pytest --cov=app --cov-branch --cov-report=term-missing --cov-report=html:branch_htmlcov
```

Open the generated HTML reports:

```powershell
start htmlcov/index.html
start branch_htmlcov/index.html
```

---

## 11. Sprint History

The project was developed incrementally through two development sprints.

| Sprint | Duration | Focus |
|---|---|---|
| Sprint 1 | October 19–25, 2026 | Core inventory functionality, dashboard, charts, low-stock alerts, and foundational application features |
| Sprint 2 | October 26–November 1, 2026 | Bug fixes, remaining SRS requirements, security and validation improvements, stock movement history, purchase order management, supplier and branch functionality, and documentation |

### Sprint Demonstrations

| Sprint | Demonstration |
|---|---|
| Sprint 1 | [View Sprint 1 Video](T9_Sprint1_Video.mp4) |
| Sprint 2 | [View Sprint 2 Video](T9_Sprint2_Video.mp4) |

---

## 12. Git and Collaboration Workflow

The project uses GitHub for source-code management, issue tracking, pull requests, and team collaboration.

The `main` branch serves as the integration branch.

### Development Workflow

1. Create a feature branch.
2. Implement the assigned feature or fix.
3. Run relevant tests locally.
4. Commit changes using descriptive commit messages.
5. Push the feature branch.
6. Open a pull request targeting `main`.
7. Review changes and address feedback.
8. Merge approved changes into the integration branch.

### Example Branch Names

```text
feature/inventory-management
feature/authentication
feature/purchase-orders
feature/stock-movement-history
test/integration-coverage
fix/api-validation
docs/project-documentation
```

### Commit Message Examples

```text
feat(auth): add login and role middleware
feat(inventory): add component CRUD endpoints
feat(inventory): generate unique SKUs
feat(purchase-orders): add partial receiving
test(inventory): add CRUD integration coverage
test(reports): cover monthly system availability
fix(frontend): correct initialization order
docs: update project documentation
ci: configure GitHub Actions workflow
```

---

## 13. Repository Structure

The repository is organized into application source code, tests, documentation, configuration, and supporting assets.

```text
Team-9-Electronics-Store-Inventory-Management-System/
│
├── app/
│   ├── monitoring/
│   ├── __init__.py
│   ├── bootstrap.py
│   ├── config.py
│   ├── db.py
│   ├── main.py
│   ├── models.py
│   ├── repositories.py
│   ├── schemas.py
│   ├── security.py
│   └── services.py
│
├── docs/
│   ├── reports/
│   │   ├── 9_Unit_Testing_Report.pdf
│   │   ├── 9_System_Validation_Report.pdf
│   │   ├── 9_Code_Coverage_Report.pdf
│   │   └── 9_Branch_Coverage_Report.pdf
│   │
│   ├── 9_SRS.pdf
│   ├── 9_SRS_updated.pdf
│   ├── 9_SAD.pd
│   ├── 9_SAD_updated.pdf
│   ├── 9_TestPlan.pdf
│   ├── 9_TestPlan_updated.pdf
│   ├── UML_diagram.png
│   ├── API.md
│   └── ARCHITECTURE.md
│
├── tests/
│   ├── integration/
│   ├── security/
│   ├── unit/
│   ├── test_integration_api.py
│   ├── test_scalability.py
│   ├── test_transport_security.py
│   ├── test_unit_security.py
│   └── test_unit_services.py
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── T9_Sprint1_Video.mp4
├── T9_Sprint2_Video.mp4
├── requirements.txt
├── run_local.py
├── run_https.py
└── README.md
```

---

## 14. Future Scope

Potential future enhancements include:

- Expanded inventory analytics and reporting.
- Additional dashboard visualizations.
- Advanced supplier and purchase order analytics.
- More comprehensive monitoring and availability tracking.
- Further security hardening.
- Additional automated test scenarios.
- Performance optimization and scalability improvements.

---

## 15. Project Information

**Project:** Electronics Store Inventory Management System (EIMS)  
**Team:** Team 9  
**Institution:** PES University  
**Application Version:** 1.1.0  
**Repository:** [Team-9-Electronics-Store-Inventory-Management-System](https://github.com/ElectronicsStore-ManagementSystem/Team-9-Electronics-Store-Inventory-Management-System)

Developed collaboratively by Team 9 as part of the Software Engineering academic project.
