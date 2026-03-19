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

## Benchmark Results

| Operation | Throughput | p50 | p99 | p999 |
|-----------|------------|-----|-----|------|
| Limit order insert | 1,196,284 orders/sec | 625 ns | 1,125 ns | 7,042 ns |
| Limit order match | 480,982 orders/sec | 2,042 ns | 7,083 ns | 14,750 ns |
| Cancel limit order | 3,636,510 orders/sec | 250 ns | 583 ns | 5,334 ns |
| Market order match | 433,576 orders/sec | 2,083 ns | 7,083 ns | 16,375 ns |
| Multi-level market order match | 93,762 orders/sec | 9,291 ns | 18,959 ns | 39,875 ns |

> Ubuntu 22.04 (Docker), Python 3.11, median of 3 runs. Each benchmark isolates a single operation with a pre-populated book to reflect realistic trading conditions. Multi-level market order match walks 5 price levels per submission.
