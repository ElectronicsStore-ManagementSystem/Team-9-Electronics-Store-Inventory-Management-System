from collections.abc import Sequence

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from .models import AuditLog, Branch, Component, StockMovement, Supplier, User

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
    branch: str | None = None,
    status: str | None = None,
    sort: str = "id",
    allow_date_sort: bool = False,
    limit: int | None = None,
    offset: int = 0,
) -> list[Component]:
    descending = sort.startswith("-")
    sort_field = sort[1:] if descending else sort
    sort_options = {
        "name": func.lower(Component.name),
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
        search_conditions = [
            Component.name.ilike(term),
            Component.sku.ilike(term),
            Component.category.ilike(term),
        ]
        category_aliases = {
            "microprocessor": "microcontroller",
            "microprocessors": "microcontroller",
        }
        category_alias = category_aliases.get(search.casefold())
        if category_alias:
            search_conditions.append(
                Component.category.ilike(f"%{category_alias}%")
            )
        query = query.where(or_(*search_conditions))
    if category:
        query = query.where(Component.category == category)
    if supplier:
        query = query.where(Component.supplier == supplier)
    if branch:
        query = query.where(Component.branch == branch)
    if status == "out-of-stock":
        query = query.where(Component.quantity == 0)
    elif status == "low-stock":
        query = query.where(
            and_(
                Component.quantity > 0,
                Component.quantity <= Component.reorder_level,
            )
        )
    elif status == "in-stock":
        query = query.where(Component.quantity > Component.reorder_level)

    query = query.order_by(
        sort_column.desc() if descending else sort_column.asc(),
        Component.id.asc(),
    )
    if limit is not None:
        query = query.limit(limit).offset(offset)
    return list(db.scalars(query))


def list_active_components(db: Session) -> list[Component]:
    return list(db.scalars(select(Component).where(Component.active.is_(True))))

def list_categories(db: Session) -> list[str]:
    return list(
        db.scalars(
            select(Component.category)
            .where(Component.active.is_(True))
            .distinct()
            .order_by(func.lower(Component.category))
        )
    )


def list_suppliers(db: Session) -> list[str]:
    names_by_normalized: dict[str, str] = {}
    supplier_names = db.scalars(
        select(Supplier.name).order_by(func.lower(Supplier.name))
    )
    component_names = db.scalars(
        select(Component.supplier).distinct().order_by(
            func.lower(Component.supplier)
        )
    )

    for name in supplier_names:
        names_by_normalized.setdefault(name.casefold(), name)
    for name in component_names:
        names_by_normalized.setdefault(name.casefold(), name)

    return sorted(names_by_normalized.values(), key=str.casefold)


def create_supplier(db: Session, name: str) -> Supplier:
    normalized_name = name.casefold()
    if any(
        existing_name.casefold() == normalized_name
        for existing_name in list_suppliers(db)
    ):
        raise ValueError("A supplier with this name already exists.")

    supplier = Supplier(name=name, normalized_name=normalized_name)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def list_branches(db: Session) -> list[str]:
    return list(
        db.scalars(
            select(Branch.name).order_by(func.lower(Branch.name))
        )
    )


def create_branch(db: Session, name: str) -> Branch:
    normalized_name = name.casefold()
    existing = db.scalar(
        select(Branch).where(Branch.normalized_name == normalized_name)
    )
    if existing is not None:
        raise ValueError("A branch with this name already exists.")

    branch = Branch(name=name, normalized_name=normalized_name)
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch


def find_branch_by_name(db: Session, name: str) -> Branch | None:
    return db.scalar(
        select(Branch).where(Branch.normalized_name == name.casefold())
    )


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


def get_dashboard_summary(db: Session) -> dict:
    """Calculate dashboard summaries directly in the database."""

    low_stock_condition = and_(
        Component.quantity > 0,
        Component.quantity <= Component.reorder_level,
    )

    # Calculate overall statistics in one database query.
    totals = db.execute(
        select(
            func.count(Component.id),
            func.coalesce(
                func.sum(Component.quantity * Component.unit_price), 0
            ),
            func.coalesce(
                func.sum(case((low_stock_condition, 1), else_=0)), 0
            ),
        ).where(Component.active.is_(True))
    ).one()

    # Get low-stock components only.
    low_stock_components = list(
        db.scalars(
            select(Component)
            .where(Component.active.is_(True), low_stock_condition)
            .order_by(Component.id)
        )
    )

    # Fetch only the five most recently added components.
    recently_added = list(
        db.scalars(
            select(Component)
            .where(Component.active.is_(True))
            .order_by(Component.created_at.desc(), Component.id.asc())
            .limit(5)
        )
    )

    # Calculate stock totals category-wise in SQL.
    category_rows = db.execute(
        select(
            Component.category,
            func.sum(Component.quantity),
            func.count(Component.id),
        )
        .where(Component.active.is_(True))
        .group_by(Component.category)
        .order_by(Component.category)
    ).all()

    # Calculate daily stock trends in SQL.
    date_column = func.date(Component.created_at)

    trend_rows = db.execute(
        select(
            date_column,
            func.sum(Component.quantity),
            func.count(Component.id),
        )
        .where(Component.active.is_(True))
        .group_by(date_column)
        .order_by(date_column)
    ).all()

    return {
        "total_components": totals[0],
        "total_stock_value": round(float(totals[1]), 2),
        "low_stock_count": totals[2],
        "low_stock_components": low_stock_components,
        "recently_added": recently_added,
        "category_stock": [
            {
                "category": category,
                "quantity": quantity,
                "component_count": count,
            }
            for category, quantity, count in category_rows
        ],
        "stock_trend": [
            {
                "date": date.isoformat() if hasattr(date, "isoformat") else str(date),
                "quantity": quantity,
                "component_count": count,
            }
            for date, quantity, count in trend_rows
        ],
    }

def create_stock_movement(
    db: Session,
    component: Component,
    user: User,
    movement_type: str,
    quantity: int,
    reason: str,
) -> StockMovement:
    movement = StockMovement(
        component_id=component.id,
        component_name=component.name,
        movement_type=movement_type,
        quantity=quantity,
        reason=reason,
        user_id=user.id,
    )

    db.add(movement)
    return movement


def list_stock_movements(
    db: Session,
    component_id: int,
) -> list[StockMovement]:
    return list(
        db.scalars(
            select(StockMovement)
            .where(StockMovement.component_id == component_id)
            .order_by(StockMovement.timestamp.desc(), StockMovement.id.desc())
        )
    )
