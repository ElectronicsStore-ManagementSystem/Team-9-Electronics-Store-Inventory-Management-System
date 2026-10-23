from .models import Component

def stock_status(component: Component) -> str:
    if component.quantity == 0:
        return "out-of-stock"
    if component.quantity <= component.reorder_level:
        return "low-stock"
    return "in-stock"

def validate_search(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip()[:120]
