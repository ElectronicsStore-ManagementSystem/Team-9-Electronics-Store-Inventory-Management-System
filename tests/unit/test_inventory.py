from backend.inventory.service import Component, validate_component, classify_stock, generate_sku

def test_validation():
    c = Component("", "IC", -1, -2, "")
    assert len(validate_component(c)) >= 4

def test_stock_classification():
    assert classify_stock(0, 5) == "out-of-stock"
    assert classify_stock(3, 5) == "low-stock"
    assert classify_stock(10, 5) == "in-stock"

def test_unique_sku_generation():
    assert generate_sku(["CMP-0001", "CMP-0003"]) == "CMP-0004"
