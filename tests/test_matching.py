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
