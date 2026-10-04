from dataclasses import dataclass
from typing import Optional

@dataclass
class Component:
    name: str
    category: str
    quantity: int
    unit_price: float
    supplier: str
    reorder_level: int = 0
    sku: Optional[str] = None

def validate_component(c: Component) -> list[str]:
    errors = []
    if not c.name.strip(): errors.append("name is required")
    if not c.category.strip(): errors.append("category is required")
    if c.quantity < 0: errors.append("quantity cannot be negative")
    if c.unit_price < 0: errors.append("unit_price cannot be negative")
    if not c.supplier.strip(): errors.append("supplier is required")
    if c.reorder_level < 0: errors.append("reorder_level cannot be negative")
    return errors

def classify_stock(quantity: int, reorder_level: int) -> str:
    if quantity == 0: return "out-of-stock"
    if quantity <= reorder_level: return "low-stock"
    return "in-stock"

def search_components(items, query: str):
    q = query.lower().strip()
    return [x for x in items if q in x.name.lower() or q in (x.sku or "").lower()
            or q in x.category.lower()]

def filter_components(items, category=None, supplier=None, status=None):
    result = items
    if category: result = [x for x in result if x.category == category]
    if supplier: result = [x for x in result if x.supplier == supplier]
    if status: result = [x for x in result if classify_stock(x.quantity, x.reorder_level) == status]
    return result

def sort_components(items, field="name", reverse=False):
    return sorted(items, key=lambda x: getattr(x, field), reverse=reverse)

def generate_sku(existing_skus, prefix="CMP"):
    nums = []
    for sku in existing_skus:
        if sku.startswith(prefix + "-"):
            try: nums.append(int(sku.split("-")[-1]))
            except ValueError: pass
    return f"{prefix}-{max(nums, default=0)+1:04d}"
