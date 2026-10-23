from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .models import Component

def stock_status(component: Component) -> str:
    if component.quantity == 0:
        return "out-of-stock"
    if component.quantity <= component.reorder_level:
        return "low-stock"
    return "in-stock"

def next_sku(db: Session) -> str:
    """
    Generate a new EIMS SKU that has never previously been assigned.

    Component IDs are used as the sequence source. Because deleted
    components remain in the database, their IDs and SKUs are preserved.
    """
    last_id = db.scalar(
        select(func.max(Component.id))
    )

    number = (last_id or 0) + 1

    while True:
        sku = f"EIMS-{number:05d}"

        existing = db.scalar(
            select(Component.id).where(Component.sku == sku)
        )

        if existing is None:
            return sku

        number += 1

def validate_search(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip()[:120]
