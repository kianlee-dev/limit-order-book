from typing import List, Optional, Callable
from .order_book import OrderBook
from .models import Order, Fill, OrderType, OrderStatus, OrderSide
from .events import EventBus, EventType

class MatchingEngine:
    def __init__(self):
        self.book = OrderBook()
        self._event_bus = EventBus()

    def on_fill(self, callback: Callable) -> None:
        self._event_bus.subscribe(EventType.ORDER_FILLED, callback)

    def submit_order(self, order: Order) -> List[Fill]:
        if order.order_type == OrderType.LIMIT:
            return self._process_limit(order)
        elif order.order_type == OrderType.MARKET:
            return self._process_market(order)
        return []

    def cancel_order(self, order_id: str) -> Optional[Order]:
        return self.book.cancel_order(order_id)

    def _process_limit(self, order: Order) -> List[Fill]:
        # if not enough liquidity for FOK order, KILL
        if order.fok:
            opposite = self.book._asks if order.side == OrderSide.BID else self.book._bids
            available = 0
            for price, queue in opposite.items():
                if order.side == OrderSide.BID and price > order.price:
                    break
                if order.side == OrderSide.ASK and price < order.price:
                    break
                available += sum(o.remaining_quantity for o in queue)
                if available >= order.quantity:
                    break
            if available < order.quantity:
                return []
            
        fills = self._match(order)
        if order.status != OrderStatus.FILLED and not order.ioc and not order.fok:
            self.book.add_limit_order(order)
        return fills

    def _process_market(self, order: Order) -> List[Fill]:
        return self._match(order)
    
    def _match(self, order: Order) -> List[Fill]:
        opposite = self.book._asks if order.side == OrderSide.BID else self.book._bids
        fills = []
        while order.status != OrderStatus.FILLED and opposite:
            best_price = next(iter(opposite))
            # limit order condition
            if order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BID:
                    if best_price > order.price:
                        break
                else:
                    if best_price < order.price:
                        break

            # FIFO for same price level
            queue = opposite[best_price]
            passive: Order = queue[0]

            trade_quantity = min(passive.remaining_quantity, order.remaining_quantity)
            trade_price = passive.price

            # update quantities
            order.filled_quantity += trade_quantity
            passive.filled_quantity += trade_quantity

            # update statuses
            order.status = OrderStatus.FILLED if order.remaining_quantity == 0 else OrderStatus.PARTIALLY_FILLED
            passive.status = OrderStatus.FILLED if passive.remaining_quantity == 0 else OrderStatus.PARTIALLY_FILLED

            fill = Fill(
            aggressor_order_id=order.order_id,
            passive_order_id=passive.order_id,
            price=trade_price,
            quantity=trade_quantity
            )
            fills.append(fill)

            # notify subscribers — decouples engine from downstream consumers
            self._event_bus.publish(EventType.ORDER_FILLED, fill)

            # Remove fully filled passive order
            if passive.status == OrderStatus.FILLED:
                queue.popleft()
                del self.book._orders[passive.order_id]
            if not queue:
                del opposite[best_price]
        return fills