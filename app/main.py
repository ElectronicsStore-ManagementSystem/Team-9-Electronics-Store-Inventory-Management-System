import csv
import os
import logging


from fastapi.responses import FileResponse, Response
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from pathlib import Path
import io
import uuid
from datetime import datetime, timezone
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
from .models import (
    AuditLog,
    AvailabilityCheck,
    Branch,
    Component,
    DowntimeIncident,
    MaintenanceWindow,
    User,
    PurchaseOrder,
   PurchaseOrderItem,
   PurchaseOrderReceipt,
   Supplier,
   Component,
   StockMovement,
)
from .schemas import (
    BranchCreate,
    BranchResponse,
    ComponentCreate,
    ComponentResponse,
    ComponentUpdate,
    DashboardResponse,
    AvailabilityResponse,
    LoginRequest,
    LoginResponse,
    SupplierCreate,
    SupplierResponse,
    StockMovementCreate,
    StockMovementResponse,
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    PurchaseOrderStatusUpdate,
    PurchaseOrderReceive,
    PurchaseOrderReceiptResponse,
)
from .security import create_access_token, get_current_user, require_admin, require_manager, verify_password
from .services import stock_status, validate_search
from .config import ENFORCE_HTTPS
from . import repositories

app = FastAPI(title="EIMS API", version="1.0.0")
logger = logging.getLogger(__name__)
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

    user.last_activity = datetime.now(timezone.utc)
    db.commit()

    return LoginResponse(access_token=create_access_token(user), role=user.role)
@app.get("/api/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "role": user.role}


def component_response_data(component: Component, user: User) -> dict:
    data = ComponentResponse.model_validate(component).model_dump()
    if user.role != "ADMIN":
        data["created_at"] = None
    return data


@app.get("/api/categories", response_model=list[str])
def get_categories(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return repositories.list_categories(db)


@app.get("/api/suppliers", response_model=list[str])
def get_suppliers(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return repositories.list_suppliers(db)


@app.post(
    "/api/suppliers",
    response_model=SupplierResponse,
    status_code=201,
)
def add_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    try:
        return repositories.create_supplier(db, payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A supplier with this name already exists.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="The supplier could not be saved due to a database error.",
        ) from exc


@app.get("/api/branches", response_model=list[str])
def get_branches(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return repositories.list_branches(db)


@app.post(
    "/api/branches",
    response_model=BranchResponse,
    status_code=201,
)
def add_branch(
    payload: BranchCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    try:
        return repositories.create_branch(db, payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A branch with this name already exists.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="The branch could not be saved due to a database error.",
        ) from exc


@app.get("/api/inventory", response_model=list[ComponentResponse])
def list_inventory(
    search: str | None = None,
    category: str | None = None,
    supplier: str | None = None,
    branch: str | None = None,
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
    branch = validate_search(branch)
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
            branch=branch,
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
        branch = repositories.find_branch_by_name(db, payload.branch)
        if branch is None:
            raise HTTPException(
                status_code=422,
                detail="Choose a branch from the branch list.",
            )
        values = payload.model_dump()
        values["branch"] = branch.name
        component = repositories.create_component(
            db,
            values,
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

@app.delete("/api/inventory/{component_id}/image")
def remove_component_image(
    component_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    component = repositories.get_active_component(db, component_id)

    if not component:
        raise HTTPException(
            status_code=404,
            detail="Component not found or inactive.",
        )

    old_image_url = component.image_url

    if not old_image_url:
        raise HTTPException(
            status_code=404,
            detail="No image is currently uploaded for this component.",
        )

    try:
        component.image_url = None
        db.commit()
        db.refresh(component)

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Image removal failed. The existing image was preserved.",
        ) from exc

    if old_image_url.startswith("/uploads/components/"):
        old_filename = Path(old_image_url).name
        old_path = UPLOAD_DIR / old_filename

        if old_path.is_file():
            try:
                old_path.unlink()
            except OSError:
                pass

    return {
        "message": "Component image removed successfully.",
        "component_id": component.id,
        "image_url": None,
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


@app.post(
    "/api/inventory/{component_id}/movements",
    response_model=StockMovementResponse,
    status_code=201,
)
def record_stock_movement(
    component_id: int,
    payload: StockMovementCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    component = repositories.get_active_component(db, component_id)

    if not component:
        raise HTTPException(status_code=404, detail="Component not found")

    if payload.movement_type == "STOCK_IN":
        component.quantity += payload.quantity

    elif payload.movement_type == "STOCK_OUT":
        if payload.quantity > component.quantity:
            raise HTTPException(
                status_code=400,
                detail="Insufficient stock available",
            )

        component.quantity -= payload.quantity

    try:
        movement = repositories.create_stock_movement(
            db,
            component,
            user,
            payload.movement_type,
            payload.quantity,
            payload.reason,
        )

        db.commit()
        db.refresh(movement)

        return movement

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Stock movement could not be recorded.",
        ) from exc

@app.get(
    "/api/inventory/{component_id}/movements",
    response_model=list[StockMovementResponse],
)
def get_stock_movement_history(
    component_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    component = repositories.get_active_component(db, component_id)

    if not component:
        raise HTTPException(
            status_code=404,
            detail="Component not found",
        )

    return repositories.list_stock_movements(db, component_id)

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

    updates = payload.model_dump(exclude_none=True)
    if "branch" in updates:
        branch = repositories.find_branch_by_name(db, updates["branch"])
        if branch is None:
            raise HTTPException(
                status_code=422,
                detail="Choose a branch from the branch list.",
            )
        updates["branch"] = branch.name

    try:
        component = repositories.update_component(
            db,
            component,
            updates,
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
    user: User = Depends(require_admin),
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

@app.get("/api/reports/availability/export")
def export_availability_report(
    format: str = Query(..., pattern="^(pdf|excel|csv)$"),
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    # Reuse the existing report so exports contain exactly the same data.
    report_data = availability(status=status, db=db, user=user)

    columns = [
        "SKU",
        "Name",
        "Category",
        "Quantity",
        "Unit Price",
        "Supplier",
        "Branch",
        "Reorder Level",
        "Stock Status",
    ]

    rows = [
        [
            item["sku"],
            item["name"],
            item["category"],
            item["quantity"],
            item["unit_price"],
            item["supplier"],
            item["branch"],
            item["reorder_level"],
            item["status"],
        ]
        for item in report_data
    ]

    output = io.BytesIO()

    if format == "csv":
        import csv

        text_output = io.StringIO()
        writer = csv.writer(text_output)
        writer.writerow(columns)
        writer.writerows(rows)

        return Response(
            content=text_output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="availability_report.csv"'
            },
        )

    if format == "excel":
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Availability Report"
        worksheet.append(columns)

        for row in rows:
            worksheet.append(row)

        workbook.save(output)

        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": 'attachment; filename="availability_report.xlsx"'
            },
        )

    # PDF export
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        title="Availability Report",
    )

    table = Table([columns] + rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243b64")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))

    document.build([table])

    return Response(
        content=output.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="availability_report.pdf"'
        },
    )


@app.get("/api/reports/system-availability")
def system_availability(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    from datetime import timedelta

    try:
        now = datetime.now(timezone.utc)

        month_start = datetime(year, month, 1, tzinfo=timezone.utc)

        if month == 12:
            month_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            month_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        # Do not calculate availability for a future period.
        reporting_end = min(month_end, now)

        if reporting_end <= month_start:
            return {
                "year": year,
                "month": month,
                "monitoring_started": False,
                "coverage_complete": False,
                "availability_percentage": None,
                "target_percentage": 99.5,
                "target_met": None,
                "message": "No monitoring period is available for this month.",
            }

        def as_utc(value):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)

        checks = db.query(AvailabilityCheck).filter(
            AvailabilityCheck.checked_at >= month_start,
            AvailabilityCheck.checked_at < reporting_end,
        ).order_by(AvailabilityCheck.checked_at).all()

        if not checks:
            return {
                "year": year,
                "month": month,
                "monitoring_started": False,
                "coverage_complete": False,
                "availability_percentage": None,
                "target_percentage": 99.5,
                "target_met": None,
                "message": "No monitoring checks were recorded for this month.",
            }

        first_check = as_utc(checks[0].checked_at)
        last_check = as_utc(checks[-1].checked_at)

        tolerance = timedelta(
            seconds=int(os.getenv("EIMS_MONITOR_INTERVAL_SECONDS", "10"))
        )

        coverage_complete = (
            first_check <= month_start + tolerance
            and last_check >= reporting_end - tolerance
        )

        coverage_start = max(first_check, month_start)
        coverage_end = min(last_check, reporting_end)

        total_seconds = (coverage_end - coverage_start).total_seconds()

        if total_seconds <= 0:
            coverage_complete = False

        def merge_intervals(intervals):
            if not intervals:
                return []

            intervals.sort(key=lambda interval: interval[0])
            merged = [intervals[0]]

            for start, end in intervals[1:]:
                previous_start, previous_end = merged[-1]

                if start <= previous_end:
                    merged[-1] = (previous_start, max(previous_end, end))
                else:
                    merged.append((start, end))

            return merged

        maintenance_windows = db.query(MaintenanceWindow).filter(
            MaintenanceWindow.start_time < coverage_end,
            MaintenanceWindow.end_time > coverage_start,
        ).all()

        maintenance_intervals = []

        for window in maintenance_windows:
            start = max(as_utc(window.start_time), coverage_start)
            end = min(as_utc(window.end_time), coverage_end)

            if end > start:
                maintenance_intervals.append((start, end))

        maintenance_intervals = merge_intervals(maintenance_intervals)

        maintenance_seconds = sum(
            (end - start).total_seconds()
            for start, end in maintenance_intervals
        )

        eligible_seconds = total_seconds - maintenance_seconds

        incidents = db.query(DowntimeIncident).filter(
            DowntimeIncident.started_at < coverage_end,
            (DowntimeIncident.ended_at.is_(None))
            | (DowntimeIncident.ended_at > coverage_start),
        ).all()

        downtime_intervals = []

        for incident in incidents:
            start = max(as_utc(incident.started_at), coverage_start)
            incident_end = (
                as_utc(incident.ended_at) if incident.ended_at else now
            )
            end = min(incident_end, coverage_end)

            if end > start:
                downtime_intervals.append((start, end))

        downtime_intervals = merge_intervals(downtime_intervals)

        # Exclude scheduled maintenance from downtime.
        unplanned_intervals = []

        for start, end in downtime_intervals:
            remaining = [(start, end)]

            for maintenance_start, maintenance_end in maintenance_intervals:
                updated = []

                for current_start, current_end in remaining:
                    if (
                        maintenance_end <= current_start
                        or maintenance_start >= current_end
                    ):
                        updated.append((current_start, current_end))
                    else:
                        if current_start < maintenance_start:
                            updated.append((current_start, maintenance_start))

                        if current_end > maintenance_end:
                            updated.append((maintenance_end, current_end))

                remaining = updated

            unplanned_intervals.extend(remaining)

        unplanned_seconds = sum(
            (end - start).total_seconds()
            for start, end in unplanned_intervals
        )

        availability_percentage = (
            (eligible_seconds - unplanned_seconds) / eligible_seconds * 100
            if eligible_seconds > 0
            else None
        )

        target_met = (
            availability_percentage >= 99.5
            if coverage_complete and availability_percentage is not None
            else None
        )

        return {
            "year": year,
            "month": month,
            "monitoring_started": True,
            "coverage_start": coverage_start.isoformat(),
            "coverage_end": coverage_end.isoformat(),
            "coverage_complete": coverage_complete,
            "total_seconds": round(total_seconds, 2),
            "scheduled_maintenance_seconds": round(maintenance_seconds, 2),
            "eligible_seconds": round(eligible_seconds, 2),
            "unplanned_downtime_seconds": round(unplanned_seconds, 2),
            "availability_percentage": (
                round(availability_percentage, 4)
                if availability_percentage is not None
                else None
            ),
            "target_percentage": 99.5,
            "target_met": target_met,
            "message": (
                "Monthly target evaluated."
                if coverage_complete
                else "Monitoring coverage is incomplete. The monthly target cannot be evaluated reliably."
            ),
        }

    except HTTPException:
        raise

    except Exception:
        db.rollback()
        logger.exception(
            "Unexpected error while generating system availability report"
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to generate the system availability report due to an unexpected error.",
        )

@app.get("/api/dashboard", response_model=DashboardResponse)
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    summary = repositories.get_dashboard_summary(db)

    return DashboardResponse(
        total_components=summary["total_components"],
        total_stock_value=summary["total_stock_value"],
        low_stock_count=summary["low_stock_count"],
        low_stock_components=[
            component_response_data(component, user)
            for component in summary["low_stock_components"]
        ],
        recently_added=[
            component_response_data(component, user)
            for component in summary["recently_added"]
        ],
        category_stock=summary["category_stock"],
        stock_trend=summary["stock_trend"],
    )


@app.get("/api/audit-logs")
def audit_logs(db: Session = Depends(get_db), user: User = Depends(require_manager)):
    rows = repositories.list_audit_logs(db)
    return [{"id": r.id, "user_id": r.user_id, "action": r.action, "component_id": r.component_id, "component_name": r.component_name, "details": r.details, "timestamp": r.timestamp} for r in rows]


# ---------------- PURCHASE ORDER APIs ----------------

@app.post(
    "/api/purchase-orders",
    response_model=PurchaseOrderResponse,
    status_code=201,
)
def create_purchase_order(
    payload: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    supplier = db.get(Supplier, payload.supplier_id)

    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")

    component_ids = [item.component_id for item in payload.items]

    if len(component_ids) != len(set(component_ids)):
        raise HTTPException(
            status_code=422,
            detail="Duplicate components are not allowed in one purchase order",
        )

    items = []

    for item in payload.items:
        component = repositories.get_active_component(db, item.component_id)

        if component is None:
            raise HTTPException(
                status_code=404,
                detail=f"Component {item.component_id} not found or inactive",
            )

        items.append({
            "component_id": component.id,
            "ordered_quantity": item.ordered_quantity,
        })

    try:
        order = repositories.create_purchase_order(
            db, supplier, user, items
        )
        db.commit()
        db.refresh(order)

        return {
            "id": order.id,
            "order_number": order.order_number,
            "supplier_id": order.supplier_id,
            "status": order.status,
            "order_date": order.order_date,
            "created_by": order.created_by,
            "items": order.items,
        }

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Purchase order creation failed",
        ) from exc


@app.get(
    "/api/purchase-orders",
    response_model=list[PurchaseOrderResponse],
)
def get_purchase_orders(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return repositories.list_purchase_orders(db)


@app.get(
    "/api/purchase-orders/{purchase_order_id}",
    response_model=PurchaseOrderResponse,
)
def get_purchase_order(
    purchase_order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = repositories.get_purchase_order(db, purchase_order_id)

    if order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    return order


@app.patch("/api/purchase-orders/{purchase_order_id}/status")
def update_purchase_order_status(
    purchase_order_id: int,
    payload: PurchaseOrderStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    order = repositories.get_purchase_order(db, purchase_order_id)

    if order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if order.status in {"RECEIVED", "CANCELLED"}:
        raise HTTPException(
            status_code=409,
            detail="This purchase order can no longer be modified",
        )

    if payload.status == "CANCELLED" and any(
        item.received_quantity > 0 for item in order.items
    ):
        raise HTTPException(
            status_code=409,
            detail="An order with received items cannot be cancelled",
        )

    if payload.status == "DRAFT" and order.status != "DRAFT":
        raise HTTPException(
            status_code=409,
            detail="An ordered purchase order cannot be moved back to draft",
        )

    try:
        order = repositories.update_purchase_order_status(
            db, order, payload.status
        )
        db.commit()
        db.refresh(order)
        return order

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Purchase order status update failed",
        ) from exc

@app.post(
    "/api/purchase-orders/{purchase_order_id}/receive",
    response_model=list[PurchaseOrderReceiptResponse],
)
def receive_purchase_order(
    purchase_order_id: int,
    payload: PurchaseOrderReceive,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    try:
        # Lock the purchase order during receiving.
        order = (
            db.query(PurchaseOrder)
            .filter(PurchaseOrder.id == purchase_order_id)
            .with_for_update()
            .first()
        )

        if order is None:
            raise HTTPException(
                status_code=404,
                detail="Purchase order not found",
            )

        if order.status in {"DRAFT", "CANCELLED", "RECEIVED"}:
            raise HTTPException(
                status_code=409,
                detail="This purchase order cannot receive additional stock",
            )

        # Check whether this receiving request was already processed.
        existing_receipt = db.query(PurchaseOrderReceipt).filter(
            PurchaseOrderReceipt.idempotency_key.like(
                f"{payload.idempotency_key}:%"
            )
        ).first()

        if existing_receipt:
            raise HTTPException(
                status_code=409,
                detail="This receiving request has already been processed",
            )

        item_ids = [
            item.purchase_order_item_id
            for item in payload.items
        ]

        if len(item_ids) != len(set(item_ids)):
            raise HTTPException(
                status_code=422,
                detail="Duplicate order items in receiving request",
            )

        # Validate every item before changing inventory.
        validated_items = []

        for received_item in payload.items:
            order_item = (
                db.query(PurchaseOrderItem)
                .filter(
                    PurchaseOrderItem.id
                    == received_item.purchase_order_item_id,
                    PurchaseOrderItem.purchase_order_id == order.id,
                )
                .with_for_update()
                .first()
            )

            if order_item is None:
                raise HTTPException(
                    status_code=404,
                    detail="Purchase order item not found",
                )

            outstanding = (
                order_item.ordered_quantity
                - order_item.received_quantity
            )

            if received_item.received_quantity > outstanding:
                raise HTTPException(
                    status_code=400,
                    detail="Received quantity exceeds outstanding quantity",
                )

            component = (
                db.query(Component)
                .filter(Component.id == order_item.component_id)
                .with_for_update()
                .first()
            )

            if component is None or not component.active:
                raise HTTPException(
                    status_code=404,
                    detail="Component not found or inactive",
                )

            validated_items.append(
                (order_item, component, received_item.received_quantity)
            )

        receipts = []

        # Apply all inventory changes in the same transaction.
        for order_item, component, quantity in validated_items:

            order_item.received_quantity += quantity
            component.quantity += quantity

            # Record receiving history with a unique key per order item.
            receipt_key = (
                f"{payload.idempotency_key}:"
                f"{order.id}:"
                f"{order_item.id}"
            )

            receipt = repositories.create_purchase_order_receipt(
                db,
                order_item,
                quantity,
                user,
                receipt_key,
            )

            receipts.append(receipt)

            # Record the inventory movement.
            db.add(
                StockMovement(
                    component_id=component.id,
                    component_name=component.name,
                    movement_type="STOCK_IN",
                    quantity=quantity,
                    reason=f"Purchase order {order.order_number} received",
                    user_id=user.id,
                )
            )

        # Calculate order status from actual received quantities.
        db.flush()

        if all(
            item.received_quantity == item.ordered_quantity
            for item in order.items
        ):
            order.status = "RECEIVED"
        else:
            order.status = "PARTIALLY_RECEIVED"

        db.commit()

        for receipt in receipts:
            db.refresh(receipt)

        return receipts

    except HTTPException:
            db.rollback()
            raise

    except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="This receiving request has already been processed",
            ) from exc

    except Exception:
       db.rollback()
    raise HTTPException(
        status_code=500,
        detail="Purchase order receiving failed",
    )


@app.get(
    "/api/purchase-orders/{purchase_order_id}/receipts",
    response_model=list[PurchaseOrderReceiptResponse],
)
def get_purchase_order_receipts(
    purchase_order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = repositories.get_purchase_order(db, purchase_order_id)

    if order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    return repositories.list_purchase_order_receipts(
        db, purchase_order_id
    )