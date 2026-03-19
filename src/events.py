from enum import Enum
from typing import Callable, Dict, List, Any

class EventType(Enum):
    ORDER_FILLED = "order_filled"
    ORDER_PARTIALLY_FILLED = "order_partially_filled"
    ORDER_CANCELLED = "order_cancelled"
    BOOK_UPDATED = "book_updated"

class EventBus:
    def __init__(self):
        self._listeners: Dict[EventType, List[Callable]] = {}

    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        self._listeners.setdefault(event_type, []).append(callback)

    def publish(self, event_type: EventType, data: Any) -> None:
        for cb in self._listeners.get(event_type, []):
            cb(data)