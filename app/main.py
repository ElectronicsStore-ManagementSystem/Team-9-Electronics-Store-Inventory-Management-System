from pathlib import Path
import io
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session
from .bootstrap import initialize_database
from .db import get_db
from .models import AuditLog, Component, User
from .schemas import ComponentCreate, ComponentResponse, ComponentUpdate, DashboardResponse, AvailabilityResponse, LoginRequest, LoginResponse
from .security import create_access_token, get_current_user, require_manager, verify_password
from .services import stock_status, validate_search
from .config import ENFORCE_HTTPS
from . import repositories

app = FastAPI(title="EIMS API", version="1.0.0")
if ENFORCE_HTTPS:
    app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"

# Component image upload configuration
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads" / "components"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
app.mount(
    "/uploads",
    StaticFiles(directory=UPLOAD_DIR.parent),
    name="uploads",
)

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
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    search = validate_search(search)
    category = validate_search(category)
    supplier = validate_search(supplier)
    if status not in {None, "in-stock", "low-stock", "out-of-stock"}:
        raise HTTPException(
            status_code=422,
            detail="Unsupported inventory status",
        )

    try:
        components = repositories.list_components(
            db,
            search=search,
            category=category,
            supplier=supplier,
            status=status,
            sort=sort,
            allow_date_sort=user.role == "ADMIN",
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="Unsupported inventory sort field",
        ) from exc

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


@app.post("/api/inventory/{component_id}/image")
async def upload_component_image(
    component_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    # Find the existing component.
    component = repositories.get_active_component(db, component_id)

    if not component:
        raise HTTPException(
            status_code=404,
            detail="Component not found or inactive.",
        )

    # Check the declared content type.
    extension = ALLOWED_IMAGE_TYPES.get(file.content_type)

    if extension is None:
        raise HTTPException(
            status_code=415,
            detail="Unsupported image format. Upload a PNG, JPEG, or WebP image.",
        )

    # Read at most 5 MB plus one byte to detect oversized uploads.
    contents = await file.read(MAX_IMAGE_SIZE + 1)
    await file.close()

    if len(contents) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds the maximum allowed size of 5 MB.",
        )

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="The uploaded image is empty.",
        )

    # Validate the actual image content, not just its extension.
    try:
        with Image.open(io.BytesIO(contents)) as image:
            actual_format = image.format

            format_extensions = {
                "JPEG": ".jpg",
                "PNG": ".png",
                "WEBP": ".webp",
            }

            if actual_format not in format_extensions:
                raise HTTPException(
                    status_code=415,
                    detail="Unsupported image format. Upload a PNG, JPEG, or WebP image.",
                )

            image.verify()

        # Ensure the MIME type matches the actual file format.
        expected_extensions = {
            "image/jpeg": {".jpg", ".jpeg"},
            "image/png": {".png"},
            "image/webp": {".webp"},
        }

        actual_extension = format_extensions[actual_format]

        if actual_extension not in expected_extensions[file.content_type]:
            raise HTTPException(
                status_code=415,
                detail="The file content does not match its declared image format.",
            )

    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=415,
            detail="The uploaded file is not a valid image.",
        ) from exc
    except (OSError, Image.DecompressionBombError) as exc:
        raise HTTPException(
            status_code=415,
            detail="The uploaded image is invalid or cannot be safely processed.",
        ) from exc

    # Save under a unique filename.
    filename = f"{uuid.uuid4().hex}{extension}"
    destination = UPLOAD_DIR / filename

    try:
        destination.write_bytes(contents)

        old_image_url = component.image_url
        component.image_url = f"/uploads/components/{filename}"

        db.commit()
        db.refresh(component)

    except Exception as exc:
        db.rollback()

        # Remove only the new file if saving the database change fails.
        try:
            if destination.exists():
                destination.unlink()
        except OSError:
            pass

        raise HTTPException(
            status_code=500,
            detail="Image upload failed. Existing component details and image were preserved.",
        ) from exc

    # Delete the previous uploaded image only after the database commit succeeds.
    if old_image_url and old_image_url.startswith("/uploads/components/"):
        old_filename = Path(old_image_url).name
        old_path = UPLOAD_DIR / old_filename

        if old_path != destination and old_path.is_file():
            try:
                old_path.unlink()
            except OSError:
                pass

    return {
        "message": "Image uploaded successfully.",
        "component_id": component.id,
        "image_url": component.image_url,
    }

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
def availability(
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    valid_statuses = {"in-stock", "low-stock", "out-of-stock"}

    if status is not None and status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid stock status. Use in-stock, low-stock, or out-of-stock.",
        )

    components = repositories.list_active_components(db)

    return [
        {
            **component_response_data(component, user),
            "status": component_status,
        }
        for component in components
        if (
            component_status := stock_status(component)
        ) == status or status is None
    ]


@app.get("/api/dashboard", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    components = repositories.list_active_components(db)
    total_value = sum(c.quantity * c.unit_price for c in components)
    low_count = sum(stock_status(c) == "low-stock" for c in components)
    low_stock_components = [
        component for component in components
        if stock_status(component) == "low-stock"
    ]
    recent = sorted(components, key=lambda c: c.created_at, reverse=True)[:5]
    category_totals: dict[str, dict[str, int]] = {}
    trend_totals: dict[str, dict[str, int]] = {}
    for component in components:
        category = category_totals.setdefault(
            component.category,
            {"quantity": 0, "component_count": 0},
        )
        category["quantity"] += component.quantity
        category["component_count"] += 1

        date = component.created_at.date().isoformat()
        trend = trend_totals.setdefault(
            date,
            {"quantity": 0, "component_count": 0},
        )
        trend["quantity"] += component.quantity
        trend["component_count"] += 1

    return DashboardResponse(
        total_components=len(components),
        total_stock_value=round(total_value, 2),
        low_stock_count=low_count,
        low_stock_components=[
            component_response_data(component, user)
            for component in low_stock_components
        ],
        recently_added=[
            component_response_data(component, user)
            for component in recent
        ],
        category_stock=[
            {"category": category, **values}
            for category, values in sorted(category_totals.items())
        ],
        stock_trend=[
            {"date": date, **trend_totals[date]}
            for date in sorted(trend_totals)
        ],
    )

@app.get("/api/audit-logs")
def audit_logs(db: Session = Depends(get_db), user: User = Depends(require_manager)):
    rows = repositories.list_audit_logs(db)
    return [{"id": r.id, "user_id": r.user_id, "action": r.action, "component_id": r.component_id, "component_name": r.component_name, "details": r.details, "timestamp": r.timestamp} for r in rows]
