from src.matching_engine import MatchingEngine
from src.models import Order, OrderSide, OrderType, OrderStatus
import uuid

def make_order(side, order_type, price, quantity, ioc=False, fok=False):
    return Order(
        order_id=str(uuid.uuid4()),
        side=side,
        order_type=order_type,
        price=price,
        quantity=quantity,
        ioc = ioc,
        fok = fok
    )

def test_time_priority():
    engine = MatchingEngine()
    buy1 = make_order(OrderSide.BID, OrderType.LIMIT, 100.0, 200)
    buy2 = make_order(OrderSide.BID, OrderType.LIMIT, 100.0, 200)
    ask = make_order(OrderSide.ASK, OrderType.LIMIT, 100.0, 100)
    engine.submit_order(buy1)
    engine.submit_order(buy2)
    assert engine.submit_order(ask)[0].passive_order_id == buy1.order_id #FIFO

def test_partial_fill():
    engine = MatchingEngine()
    buy = make_order(OrderSide.BID, OrderType.LIMIT, 100.0, 100)
    sell = make_order(OrderSide.ASK, OrderType.LIMIT, 100.0, 60)
    engine.submit_order(buy)
    fills = engine.submit_order(sell)
    assert buy.filled_quantity == 60 and buy.status == OrderStatus.PARTIALLY_FILLED and fills[0].quantity == 60

def test_full_fill_clears_book():
    engine = MatchingEngine()
    buy = make_order(OrderSide.BID, OrderType.LIMIT, 100.0, 50)
    sell = make_order(OrderSide.ASK, OrderType.LIMIT, 100.0, 50)
    engine.submit_order(buy)
    engine.submit_order(sell)
    assert engine.book.get_order(buy.order_id) is None

def test_cancel_non_existent():
    engine = MatchingEngine()
    result = engine.cancel_order("dummy-id")
    assert result is None

def test_market_order_empty_book():
    engine = MatchingEngine()
    buy = make_order(OrderSide.BID, OrderType.MARKET, None, 100)
    assert engine.submit_order(buy) == []

def test_price_priority():
    engine = MatchingEngine()
    ask1 = make_order(OrderSide.ASK, OrderType.LIMIT, 120.0, 100)
    ask2 = make_order(OrderSide.ASK, OrderType.LIMIT, 100.0, 100)
    buy = make_order(OrderSide.BID, OrderType.MARKET, None, 100)
    engine.submit_order(ask1)
    engine.submit_order(ask2)
    fill = engine.submit_order(buy)[0]
    # best ask filled first
    assert fill.passive_order_id == ask2.order_id

def test_ioc_unfilled_cancelled():
    engine = MatchingEngine()
    ask = make_order(OrderSide.ASK, OrderType.LIMIT, 100.0, 50)
    buy = make_order(OrderSide.BID, OrderType.LIMIT, 100.0, 100, ioc = True)
    engine.submit_order(ask)
    fill = engine.submit_order(buy)[0]
    # check partially filled quantity, remainder cancelled
    assert engine.book.get_order(buy.order_id) is None and fill.quantity == 50

def test_fok_cancelled_if_unfillable():
    engine = MatchingEngine()
    ask = make_order(OrderSide.ASK, OrderType.LIMIT, 100.0, 50)
    buy = make_order(OrderSide.BID, OrderType.LIMIT, 100.0, 100, fok = True)
    engine.submit_order(ask)
    fills = engine.submit_order(buy)
    # no fill took place if unfillable and fok
    assert  fills == [] and engine.book.get_order(buy.order_id) is None

def test_fok_fills_if_fully_fillable():
    engine = MatchingEngine()
    ask = make_order(OrderSide.ASK, OrderType.LIMIT, 100.0, 100)
    buy = make_order(OrderSide.BID, OrderType.LIMIT, 100.0, 50, fok = True)
    engine.submit_order(ask)
    fill = engine.submit_order(buy)[0]
    assert fill.passive_order_id == ask.order_id and fill.quantity == 50 and engine.book.get_order(ask.order_id) is not None

def test_ioc_full_fill():
    engine = MatchingEngine()
    ask = make_order(OrderSide.ASK, OrderType.LIMIT, 100.0, 100)
    buy = make_order(OrderSide.BID, OrderType.LIMIT, 100.0, 50, ioc = True)
    engine.submit_order(ask)
    fill = engine.submit_order(buy)[0]
    assert fill.passive_order_id == ask.order_id and fill.quantity == 50 and engine.book.get_order(buy.order_id) is None

def test_price_no_match():
    engine = MatchingEngine()
    ask = make_order(OrderSide.ASK, OrderType.LIMIT, 101.0, 100)
    buy = make_order(OrderSide.BID, OrderType.LIMIT, 99.0, 100)
    engine.submit_order(ask)
    fills = engine.submit_order(buy)
    assert fills == [] and engine.book.get_order(ask.order_id) is not None and engine.book.get_order(buy.order_id) is not None

def test_market_order_walks_levels():
    engine = MatchingEngine()
    ask1 = make_order(OrderSide.ASK, OrderType.LIMIT, 100.0, 10)
    ask2 = make_order(OrderSide.ASK, OrderType.LIMIT, 120.0, 30)
    ask3 = make_order(OrderSide.ASK, OrderType.LIMIT, 140.0, 90)
    buy  = make_order(OrderSide.BID, OrderType.MARKET, None, 150)
    engine.submit_order(ask1)
    engine.submit_order(ask2)
    engine.submit_order(ask3)
    fills = engine.submit_order(buy)
    assert len(fills) == 3 and buy.remaining_quantity == 20
    # market order should not rest in book
    assert engine.book.get_order(buy.order_id) is None

