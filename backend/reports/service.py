from backend.inventory.service import classify_stock

def availability_report(items):
    return [{"sku": x.sku, "name": x.name, "quantity": x.quantity,
             "status": classify_stock(x.quantity, x.reorder_level)}
            for x in items]

def filter_report(rows, category=None, supplier=None, status=None):
    # Expected row shape can be extended with category/supplier fields by the API layer.
    result = rows
    if status:
        result = [r for r in result if r["status"] == status]
    return result

def stock_value(items):
    return sum(x.quantity * x.unit_price for x in items)
