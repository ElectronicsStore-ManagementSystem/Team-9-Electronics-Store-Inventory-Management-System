from backend.reports.service import stock_value
def test_stock_value():
    class X: quantity=2; unit_price=50
    assert stock_value([X()]) == 100
