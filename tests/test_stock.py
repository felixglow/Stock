"""
股票数据模块测试
"""
from src.stock import Stock

# 测试数据常量
TEST_STOCK_CODE = "sz002230"
TEST_STOCK_NAME = "科大讯飞"
TEST_CURRENT_PRICE = 43.39
TEST_CHANGE_PERCENT = -10.00
TEST_HIGH_PRICE = 45.80
TEST_LOW_PRICE = 43.39
TEST_VOLUME = 48001952
TEST_AMOUNT = 2122000000.0
TEST_THREAD_COUNT = 3

def test_stock_initialization():
    """测试股票对象初始化"""
    stock = Stock(TEST_STOCK_CODE, TEST_THREAD_COUNT)
    assert stock.code == TEST_STOCK_CODE
    assert len(stock.threads) == TEST_THREAD_COUNT

def test_stock_data_fetch():
    """测试股票数据获取"""
    stock = Stock(TEST_STOCK_CODE, 1)
    result = stock.value_get(TEST_STOCK_CODE, 0)
    
    assert result is not None
    code_index, data = result
    assert code_index == 0
    assert isinstance(data, tuple)
    name, price, change = data
    assert name == TEST_STOCK_NAME
    assert float(price) > 0

def test_stock_data_creation():
    """测试股票数据对象创建"""
    stock = Stock(TEST_STOCK_CODE, TEST_THREAD_COUNT)
    result = stock.value_get(TEST_STOCK_CODE, 0)
    assert result is not None
    code_index, data = result
    assert code_index == 0
    name, price, change = data
    assert name == TEST_STOCK_NAME
    assert float(price) > 0

def test_stock_data_from_sina_api():
    """测试从新浪API获取数据"""
    code = TEST_STOCK_CODE
    data = f"{TEST_STOCK_NAME},{TEST_HIGH_PRICE},48.21,{TEST_CURRENT_PRICE}," \
           f"{TEST_HIGH_PRICE},{TEST_LOW_PRICE},{TEST_CURRENT_PRICE}," \
           f"{TEST_CURRENT_PRICE},{TEST_VOLUME},{TEST_AMOUNT},..."
    
    stock = Stock(code)
    result = stock.value_get(code, 0)
    assert result is not None
    code_index, data = result
    assert code_index == 0
    name, price, _ = data
    assert name == TEST_STOCK_NAME
    assert float(price) > 0

def test_stock_api_get_data():
    """测试股票API数据获取"""
    stock = Stock(TEST_STOCK_CODE)
    result = stock.value_get(TEST_STOCK_CODE, 0)
    assert result is not None
    code_index, data = result
    assert code_index == 0
    name, price, _ = data
    assert name == TEST_STOCK_NAME
    assert float(price) > 0