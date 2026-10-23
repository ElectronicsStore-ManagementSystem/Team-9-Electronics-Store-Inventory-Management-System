from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from .db import Base, engine, get_db, SessionLocal
from .models import AuditLog, Component, User
from .schemas import ComponentCreate, ComponentResponse, ComponentUpdate, DashboardResponse, AvailabilityResponse, LoginRequest, LoginResponse
from .security import create_access_token, get_current_user, hash_password, require_manager, verify_password
from .services import next_sku, stock_status, validate_search

Base.metadata.create_all(bind=engine)
app = FastAPI(title="EIMS API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

def seed():
    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.username == "admin")):
            return
        db.add_all([
            User(username="admin", password_hash=hash_password("Admin@12345"), role="ADMIN"),
            User(username="staff", password_hash=hash_password("Staff@12345"), role="STAFF"),
        ])
        db.flush()
        db.add_all([
            Component(sku="EIMS-00001", name="Arduino Uno", category="Microcontroller", quantity=18, unit_price=650, supplier="TechSource", reorder_level=5),
            Component(sku="EIMS-00002", name="ESP32 Dev Board", category="Microcontroller", quantity=4, unit_price=520, supplier="TechSource", reorder_level=5),
            Component(sku="EIMS-00003", name="220 Ohm Resistor", category="Passive", quantity=0, unit_price=2.5, supplier="CircuitHub", reorder_level=20),
        ])
        db.commit()
    finally:
        db.close()

seed()

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(FRONTEND / "index.html")

@app.get("/health")
def health():
    return {"status": "ok", "service": "eims-api"}

@app.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username.strip()))
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

    query = select(Component).where(Component.active.is_(True))

    if search:
        term = f"%{search}%"
        query = query.where(
            or_(
                Component.name.ilike(term),
                Component.sku.ilike(term),
                Component.category.ilike(term),
            )
        )

    if category:
        query = query.where(Component.category == category)

    if supplier:
        query = query.where(Component.supplier == supplier)

    descending = sort.startswith("-")
    sort_field = sort[1:] if descending else sort

    sort_options = {
        "quantity": Component.quantity,
        "unit_price": Component.unit_price,
        "price": Component.unit_price,
        "id": Component.id,
    }
    if user.role == "ADMIN":
        sort_options.update({
            "date_added": Component.created_at,
            "date": Component.created_at,
        })

    sort_column = sort_options.get(sort_field)

    if sort_column is None:
        raise HTTPException(
            status_code=422,
            detail="Unsupported inventory sort field",
        )

    query = query.order_by(
        sort_column.desc() if descending else sort_column.asc(),
        Component.id.asc(),
    )
    components = list(db.scalars(query))

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
        sku = next_sku(db)

        if not sku or not sku.startswith("EIMS-"):
            raise HTTPException(
                status_code=500,
                detail="Unable to generate a valid component SKU.",
            )

        component = Component(
            sku=sku,
            **payload.model_dump(),
        )

        db.add(component)
        db.commit()
        db.refresh(component)

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
    component = db.get(Component, component_id)
    if not component or not component.active:
        raise HTTPException(status_code=404, detail="Component not found")
    return component_response_data(component, user)

@app.patch("/api/inventory/{component_id}", response_model=ComponentResponse)
def update_component(component_id: int, payload: ComponentUpdate, db: Session = Depends(get_db), user: User = Depends(require_manager)):
    component = db.get(Component, component_id)
    if not component or not component.active:
        raise HTTPException(status_code=404, detail="Component not found")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(component, key, value.strip() if key == "supplier" else value)
    db.commit()
    db.refresh(component)
    return component

@app.delete("/api/inventory/{component_id}")
def delete_component(component_id: int, db: Session = Depends(get_db), user: User = Depends(require_manager)):
    component = db.get(Component, component_id)
    if not component or not component.active:
        raise HTTPException(status_code=404, detail="Component not found")
    component.active = False
    db.add(AuditLog(user_id=user.id, action="DELETE_COMPONENT", component_id=component.id, component_name=component.name, details=f"Deleted SKU {component.sku}"))
    db.commit()
    return {"status": "deleted", "component_id": component.id}

@app.get("/api/reports/availability", response_model=list[AvailabilityResponse])
def availability(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    components = list(db.scalars(select(Component).where(Component.active.is_(True))))
    return [
        {
            **component_response_data(component, user),
            "status": stock_status(component),
        }
        for component in components
    ]

@app.get("/api/dashboard", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    components = list(db.scalars(select(Component).where(Component.active.is_(True))))
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
    rows = list(db.scalars(select(AuditLog).order_by(AuditLog.timestamp.desc())))
    return [{"id": r.id, "user_id": r.user_id, "action": r.action, "component_id": r.component_id, "component_name": r.component_name, "details": r.details, "timestamp": r.timestamp} for r in rows]
