import pytest
from src.matching_engine import MatchingEngine
from src.models import Order, OrderSide, OrderType
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