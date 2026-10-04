from backend.dashboard.service import dashboard_summary
def test_dashboard_summary():
    class X: quantity=2; unit_price=10; reorder_level=3
    r = dashboard_summary([X()])
    assert r["total_components"] == 1
    assert r["low_stock_count"] == 1
