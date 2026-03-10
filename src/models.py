from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time

class OrderSide(Enum):
    BID = "bid" # buyer side 
    ASK = "ask" # seller side

class OrderType(Enum):
    LIMIT = "limit" # rests in book if unmatched
    MARKET = "market" # executes immediately at best available price

class OrderStatus(Enum):
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled" # includes IOC/FOK remainder

@dataclass
class Order:
    order_id: str
    side: OrderSide
    order_type: OrderType
    price: Optional[float] # could be none for market orders, they have no specific prices
    quantity: int
    timestamp: int = field(default_factory=lambda: time.perf_counter_ns())  # nanosecond precision for latency benchmarking
    filled_quantity: int = 0
    status: OrderStatus = OrderStatus.OPEN # default is OPEN

@dataclass
class Fill:
    aggressor_order_id: str # incoming order that triggered the match
    passive_order_id:str # resting order that was already in the book
    price: float # always the passive order's price
    quantity: int
    timestamp: int = field(default_factory=lambda: time.perf_counter_ns())
