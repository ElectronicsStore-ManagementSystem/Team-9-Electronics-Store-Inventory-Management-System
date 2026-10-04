def dashboard_summary(items):
    return {
        "total_components": len(items),
        "total_stock_value": sum(x.quantity * x.unit_price for x in items),
        "low_stock_count": sum(1 for x in items if x.quantity <= x.reorder_level and x.quantity > 0),
        "recently_added": items[-5:]
    }

def category_counts(items):
    counts = {}
    for x in items:
        counts[x.category] = counts.get(x.category, 0) + 1
    return counts
