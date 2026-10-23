from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .models import AuditLog, Component, User


def find_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def insert_seed_records(
    db: Session,
    users: Sequence[User],
    components: Sequence[Component],
) -> None:
    db.add_all(users)
    db.flush()
    db.add_all(components)
    db.commit()


def list_components(
    db: Session,
    *,
    search: str | None = None,
    category: str | None = None,
    supplier: str | None = None,
    sort: str = "id",
    allow_date_sort: bool = False,
) -> list[Component]:
    descending = sort.startswith("-")
    sort_field = sort[1:] if descending else sort
    sort_options = {
        "quantity": Component.quantity,
        "unit_price": Component.unit_price,
        "price": Component.unit_price,
        "id": Component.id,
    }
    if allow_date_sort:
        sort_options.update({
            "date_added": Component.created_at,
            "date": Component.created_at,
        })

    sort_column = sort_options.get(sort_field)
    if sort_column is None:
        raise ValueError("Unsupported inventory sort field")

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

    query = query.order_by(
        sort_column.desc() if descending else sort_column.asc(),
        Component.id.asc(),
    )
    return list(db.scalars(query))


def list_active_components(db: Session) -> list[Component]:
    return list(db.scalars(select(Component).where(Component.active.is_(True))))


def get_active_component(db: Session, component_id: int) -> Component | None:
    component = db.get(Component, component_id)
    if component is None or not component.active:
        return None
    return component


def create_component(db: Session, values: dict) -> Component:
    last_id = db.scalar(select(func.max(Component.id)))
    number = (last_id or 0) + 1

    while True:
        sku = f"EIMS-{number:05d}"
        existing_id = db.scalar(
            select(Component.id).where(Component.sku == sku)
        )
        if existing_id is None:
            break
        number += 1

    component = Component(sku=sku, **values)
    db.add(component)
    db.commit()
    db.refresh(component)
    return component


def update_component(
    db: Session,
    component: Component,
    values: dict,
) -> Component:
    for key, value in values.items():
        setattr(component, key, value)
    db.commit()
    db.refresh(component)
    return component


def deactivate_component(
    db: Session,
    component: Component,
    audit_log: AuditLog,
) -> None:
    component.active = False
    db.add(audit_log)
    db.commit()


def list_audit_logs(db: Session) -> list[AuditLog]:
    return list(
        db.scalars(select(AuditLog).order_by(AuditLog.timestamp.desc()))
    )
