"""
Order book data structure — storage and indexing only, no matching logic.

Bids and asks stored in SortedDict for O(1) best-price access.
Separate order index enables O(1) cancel by order_id.
"""

from sortedcontainers import SortedDict
from typing import Dict
from .models import Order, OrderSide
from collections import deque

class OrderBook:
    def __init__(self):
        # asks: sorted by lowest price
        self._asks: SortedDict = SortedDict()
        # bids: highest price first, keys negated to sort in descending order
        self._bids: SortedDict = SortedDict(lambda x: -x)
        # O(1) lookup for cancels and modifies
        self._orders: Dict[str, Order] = {}

    def add_limit_order(self, order: Order) -> None:
        book = self._asks if order.side == OrderSide.ASK else self._bids
        if order.price not in book:
            book[order.price] = deque() # initialise first seen price level
        book[order.price].append(order)
        self._orders[order.order_id] = order # flat index reference for O(1) cancel operation
