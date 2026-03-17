from src.matching_engine import MatchingEngine
from src.models import Order, OrderSide, OrderType, OrderStatus
import uuid

def make_order(side, order_type, price, quantity):
    return Order(
        order_id=str(uuid.uuid4()),
        side=side,
        order_type=order_type,
        price=price,
        quantity=quantity
    )

def test_time_priority():
    engine = MatchingEngine()
    buy1 = make_order(OrderSide.BID, OrderType.LIMIT, 100.0, 200)
    buy2 = make_order(OrderSide.BID, OrderType.LIMIT, 100.0, 200)
    ask = make_order(OrderSide.ASK, OrderType.LIMIT, 100.0, 100)
    engine.submit_order(buy1)
    engine.submit_order(buy2)
    assert engine.submit_order(ask)[0].passive_order_id == buy1.order_id

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
