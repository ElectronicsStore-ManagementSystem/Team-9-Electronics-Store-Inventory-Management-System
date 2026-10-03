from app.services import stock_status, validate_search
from app.models import Component

def make(qty,reorder): return Component(quantity=qty,reorder_level=reorder)

def test_stock_status_in_stock(): assert stock_status(make(10,5)) == 'in-stock'
def test_stock_status_low_stock_boundary(): assert stock_status(make(5,5)) == 'low-stock'
def test_stock_status_out_of_stock_boundary(): assert stock_status(make(0,5)) == 'out-of-stock'
def test_search_input_trimmed_and_limited(): assert validate_search('  abc  ') == 'abc'; assert len(validate_search('x'*200)) == 120
