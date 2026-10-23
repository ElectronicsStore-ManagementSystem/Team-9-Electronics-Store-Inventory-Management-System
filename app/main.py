from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from .bootstrap import initialize_database
from .db import get_db
from .models import AuditLog, Component, User
from .schemas import ComponentCreate, ComponentResponse, ComponentUpdate, DashboardResponse, AvailabilityResponse, LoginRequest, LoginResponse
from .security import create_access_token, get_current_user, require_manager, verify_password
from .services import stock_status, validate_search
from . import repositories

app = FastAPI(title="EIMS API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

initialize_database()

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(FRONTEND / "index.html")

@app.get("/health")
def health():
    return {"status": "ok", "service": "eims-api"}

@app.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = repositories.find_user_by_username(db, payload.username.strip())
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return LoginResponse(access_token=create_access_token(user), role=user.role)

@app.get("/api/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "role": user.role}


def component_response_data(component: Component, user: User) -> dict:
    data = ComponentResponse.model_validate(component).model_dump()
    if user.role != "ADMIN":
        data["created_at"] = None
    return data


@app.get("/api/inventory", response_model=list[ComponentResponse])
def list_inventory(
    search: str | None = None,
    category: str | None = None,
    supplier: str | None = None,
    status: str | None = None,
    sort: str = Query(default="id"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    search = validate_search(search)
    category = validate_search(category)
    supplier = validate_search(supplier)

    try:
        components = repositories.list_components(
            db,
            search=search,
            category=category,
            supplier=supplier,
            sort=sort,
            allow_date_sort=user.role == "ADMIN",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="Unsupported inventory sort field",
        ) from exc

    if status:
        components = [
            component for component in components
            if stock_status(component) == status
        ]

    return [component_response_data(component, user) for component in components]


@app.post("/api/inventory", response_model=ComponentResponse, status_code=201)
def add_component(
    payload: ComponentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    try:
        component = repositories.create_component(
            db,
            payload.model_dump(),
        )
        return component

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The component could not be saved because of a duplicate or conflicting identifier. Please try again.",
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="The component could not be saved due to a database error.",
        ) from exc

@app.get("/api/inventory/{component_id}", response_model=ComponentResponse)
def get_component(
    component_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    component = repositories.get_active_component(db, component_id)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    return component_response_data(component, user)

@app.patch("/api/inventory/{component_id}", response_model=ComponentResponse)
def update_component(
    component_id: int,
    payload: ComponentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    component = repositories.get_active_component(db, component_id)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")

    try:
        component = repositories.update_component(
            db,
            component,
            payload.model_dump(exclude_none=True),
        )
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="The component could not be updated due to a database error.",
        ) from exc

    return component_response_data(component, user)

@app.delete("/api/inventory/{component_id}")
def delete_component(component_id: int, db: Session = Depends(get_db), user: User = Depends(require_manager)):
    component = repositories.get_active_component(db, component_id)
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")
    repositories.deactivate_component(
        db,
        component,
        AuditLog(
            user_id=user.id,
            action="DELETE_COMPONENT",
            component_id=component.id,
            component_name=component.name,
            details=f"Deleted SKU {component.sku}",
        ),
    )
    return {"status": "deleted", "component_id": component.id}

@app.get("/api/reports/availability", response_model=list[AvailabilityResponse])
def availability(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    components = repositories.list_active_components(db)
    return [
        {
            **component_response_data(component, user),
            "status": stock_status(component),
        }
        for component in components
    ]

@app.get("/api/dashboard", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    components = repositories.list_active_components(db)
    total_value = sum(c.quantity * c.unit_price for c in components)
    low_count = sum(stock_status(c) == "low-stock" for c in components)
    recent = sorted(components, key=lambda c: c.created_at, reverse=True)[:5]
    return DashboardResponse(
        total_components=len(components),
        total_stock_value=round(total_value, 2),
        low_stock_count=low_count,
        recently_added=[
            component_response_data(component, user)
            for component in recent
        ],
    )

@app.get("/api/audit-logs")
def audit_logs(db: Session = Depends(get_db), user: User = Depends(require_manager)):
    rows = repositories.list_audit_logs(db)
    return [{"id": r.id, "user_id": r.user_id, "action": r.action, "component_id": r.component_id, "component_name": r.component_name, "details": r.details, "timestamp": r.timestamp} for r in rows]
