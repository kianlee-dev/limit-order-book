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

## Test Coverage

12 tests, all passing. Written before the matching engine — test-driven development.

**Core behaviour**

| Test | What it verifies |
|------|-----------------|
| `test_time_priority` | First order at a price level fills before later orders at the same price |
| `test_partial_fill` | Order remains open with correct filled_quantity after partial match |
| `test_full_fill_clears_book` | Fully filled order is removed from the book |
| `test_price_priority` | Best priced order fills before worse priced order |

**Edge cases**

| Test | What it verifies |
|------|-----------------|
| `test_cancel_non_existent` | Cancelling an unknown order_id returns None safely |
| `test_market_order_empty_book` | Market order on empty book returns no fills |
| `test_ioc_unfilled_cancelled` | IOC remainder is cancelled after partial fill |
| `test_fok_cancelled_if_unfillable` | FOK order is killed entirely if full quantity unavailable |
| `test_fok_fills_if_fully_fillable` | FOK order fills completely when liquidity is sufficient |
| `test_ioc_full_fill` | IOC order that fills completely leaves no resting order |
| `test_price_no_match` | Limit orders with no crossing price rest in book without matching |
| `test_market_order_walks_levels` | Market order consumes multiple price levels until filled |

## Benchmark Results

| Operation | Throughput | p50 | p99 | p999 |
|-----------|------------|-----|-----|------|
| Limit order insert | 1,196,284 orders/sec | 625 ns | 1,125 ns | 7,042 ns |
| Limit order match | 480,982 orders/sec | 2,042 ns | 7,083 ns | 14,750 ns |
| Cancel limit order | 3,636,510 orders/sec | 250 ns | 583 ns | 5,334 ns |
| Market order match | 433,576 orders/sec | 2,083 ns | 7,083 ns | 16,375 ns |
| Multi-level market order match | 93,762 orders/sec | 9,291 ns | 18,959 ns | 39,875 ns |

> Ubuntu 22.04 (Docker), Python 3.11, median of 3 runs. Each benchmark isolates a single operation with a pre-populated book to reflect realistic trading conditions. Multi-level market order match walks 5 price levels per submission.

### Analysis

The results reflect the mechanical cost of each operation through the engine. Cancel is the fastest at 3.6M ops/sec — it is a pure O(1) hashmap lookup with no matching logic or object creation. Limit insert is second at 1.2M ops/sec, requiring only a SortedDict insertion with no fill computation. Limit and market order match are slower at ~480k and ~433k ops/sec respectively, as both run the full match loop, construct Fill objects, and publish events through the event bus. Multi-level market order match is the slowest at 93k ops/sec — each order walks 5 price levels, multiplying match loop iterations 5x compared to single-level market match, which is reflected in the p999 jumping to 39,875 ns.

These numbers reflect Python interpreter overhead rather than the hardware's true ceiling. The GIL prevents parallel order processing, and Python object allocation adds latency that a C++ implementation would eliminate entirely. Production matching engines in high-frequency trading operate in the tens of nanoseconds range using lock-free data structures and cache-optimised memory layouts. Additionally, this engine is single-threaded by design — introducing multi-threaded order ingestion without proper synchronisation would introduce race conditions on shared book state, requiring either a mutex around the matching critical section or a lock-free SPSC ring buffer for order ingestion to maintain correctness under concurrency.

## How to Run

**Build the image**
```bash
docker build -t limit-order-book .
```

**Run tests**
```bash
docker run -v $(pwd):/app limit-order-book pytest tests/ -v
```

**Run replay demo**
```bash
docker run -v $(pwd):/app limit-order-book python examples/replay.py
```

**Run benchmarks**
```bash
docker run -v $(pwd):/app limit-order-book python benchmarks/bench.py
```

## Limitations and Future Work

**Current limitations**
- Python GIL prevents true multi-threaded order processing
- No persistent storage — order state lives in memory only
- Benchmark numbers reflect Python overhead, not hardware limits

**Natural next steps**
- Port matching engine core to C++ for sub-microsecond latency
- Add lock-free SPSC ring buffer for order ingestion
- Implement ITCH 5.0 protocol parser for real exchange feed consumption
- Thread-pinning and CPU affinity for deterministic latency
