# Limit Order Book

A price-time priority matching engine implementing limit orders, market orders, IOC/FOK, and a pub/sub event system. Built to demonstrate data structure selection, performance measurement, and financial systems domain knowledge.

## Project Structure
```
limit-order-book/
├── src/
│   ├── models.py          # Data contracts — Order, Fill, enums
│   ├── order_book.py      # Data structure — storage, insert, cancel, query
│   ├── matching_engine.py # Business logic — matching algorithm
│   └── events.py          # Pub/sub event bus
├── tests/
│   └── test_matching.py   # 12 tests, written before engine
├── benchmarks/
│   └── bench.py           # Throughput and latency benchmarks
├── examples/
│   └── replay.py          # CSV replay demo
└── requirements.txt
```

## Architecture
```
Orders
  │
  ▼
MatchingEngine          EventBus
  │    └─────────────────────┤
  │                          │ publishes fills
  ▼                          │
OrderBook              subscribers
  │                    (callbacks)
  ▼
Models
(Order, Fill, Enums)
```

## Single Responsibility

| File | Responsibility | Justification |
|------|---------------|---------------|
| `models.py` | Data contracts only | Zero logic — prevents circular dependencies |
| `order_book.py` | Storage and indexing | Book integrity testable independently of matching |
| `matching_engine.py` | Matching algorithm | Can swap book implementation without touching algorithm |
| `events.py` | Pub/sub event bus | Engine publishes fills without knowing who listens |

## Design Decisions

**SortedDict for price levels, not a regular dict**
Regular dict has O(1) lookup but no ordering. Matching requires iterating from best to worst price. SortedDict from sortedcontainers gives O(log n) insert and O(1) access to min/max — exactly the access pattern a matching engine needs.

**Deque per price level, not a list**
Time priority requires FIFO within each price level. deque gives O(1) append and O(1) popleft. A list gives O(n) popleft because it shifts all elements. On a hot path processing millions of orders that difference compounds.

**Separate order index for O(1) cancel**
A flat dict keyed by order_id maps directly to the Order object. Cancel is O(1) lookup, then removal from the price level deque. Without this index, cancel would require scanning every price level.

**OrderBook separated from MatchingEngine**
OrderBook is a data structure problem — maintaining state correctly. MatchingEngine is a business logic problem — the matching algorithm. Separating them means book integrity is testable independently of matching logic, and the book implementation can be swapped without touching the algorithm.

**Event bus instead of direct callbacks**
The engine publishes fills without knowing who is listening. A risk system, logger, or P&L calculator can subscribe without any changes to the engine. This mirrors real OMS architecture where the matching engine is decoupled from downstream consumers.

**IOC and FOK as proper dataclass fields**
`ioc: bool = False` and `fok: bool = False` are declared directly on the Order dataclass rather than using `getattr` workarounds.

**`remaining_quantity` as a computed property**
`quantity - filled_quantity` is computed in one place on the Order dataclass rather than repeated at every callsite in the match loop. Eliminates a class of bugs where the calculation could be written differently in different places.

## Data Structure Complexity

| Operation | Structure | Complexity | Reason |
|-----------|-----------|------------|--------|
| Limit order insert | SortedDict | O(log n) | Tree-based insertion |
| Cancel order | dict[order_id] | O(1) | Direct hashmap lookup |
| Best bid/ask | SortedDict first key | O(1) | Sorted structure, first element |
| Price level traversal | SortedDict iteration | O(log n) | Tree-based iteration |
| Time priority | deque per price level | O(1) | FIFO append/popleft |

## Order Types Supported

- **Limit** — rests in the book at a specified price if not immediately matchable
- **Market** — executes immediately at the best available price, walks price levels
- **IOC (Immediate or Cancel)** — fills whatever is available, cancels the remainder
- **FOK (Fill or Kill)** — fills the entire quantity or cancels entirely, nothing partial
- **Cancel** — removes a resting order from the book in O(1)

## Benchmark Results

| Operation | Throughput | p50 | p99 | p999 |
|-----------|------------|-----|-----|------|
| Limit order insert | 1,196,284 orders/sec | 625 ns | 1,125 ns | 7,042 ns |
| Limit order match | 480,982 orders/sec | 2,042 ns | 7,083 ns | 14,750 ns |
| Cancel limit order | 3,636,510 orders/sec | 250 ns | 583 ns | 5,334 ns |
| Market order match | 433,576 orders/sec | 2,083 ns | 7,083 ns | 16,375 ns |
| Multi-level market order match | 93,762 orders/sec | 9,291 ns | 18,959 ns | 39,875 ns |

> Ubuntu 22.04 (Docker), Python 3.11, median of 3 runs. Each benchmark isolates a single operation with a pre-populated book to reflect realistic trading conditions. Multi-level market order match walks 5 price levels per submission.
