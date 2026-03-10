from enum import Enum

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