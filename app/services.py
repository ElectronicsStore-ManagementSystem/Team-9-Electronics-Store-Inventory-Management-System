from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Component

def stock_status(component: Component) -> str:
    if component.quantity == 0:
        return "out-of-stock"
    if component.quantity <= component.reorder_level:
        return "low-stock"
    return "in-stock"

def next_sku(db: Session) -> str:
    last = db.scalar(select(Component).order_by(Component.id.desc()).limit(1))
    number = (last.id + 1) if last else 1
    return f"EIMS-{number:05d}"

def validate_search(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip()[:120]
