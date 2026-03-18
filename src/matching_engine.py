from typing import List, Optional
from .order_book import OrderBook
from .models import Order, Fill, OrderType, OrderStatus

class MatchingEngine:
    def __init__(self):
        self.book = OrderBook()

    def submit_order(self, order: Order) -> List[Fill]:
        if order.order_type == OrderType.LIMIT:
            return self._process_limit(order)
        elif order.order_type == OrderType.MARKET:
            return self._process_market(order)
        return []

    def cancel_order(self, order_id: str) -> Optional[Order]:
        return self.book.cancel_order(order_id)

    def _process_limit(self, order: Order) -> List[Fill]:
        fills = self._match(order)
        if order.status != OrderStatus.FILLED and not order.ioc and not order.fok:
            self.book.add_limit_order(order)
        return fills

    def _process_market(self, order: Order) -> List[Fill]:
        return self._match(order)
    
    def _match(self, order: Order) -> List[Fill]:
        return []