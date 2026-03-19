## Benchmark Results

| Operation | Throughput | p50 | p99 | p999 |
|-----------|------------|-----|-----|------|
| Limit order insert | 1,196,284 orders/sec | 625 ns | 1,125 ns | 7,042 ns |
| Limit order match | 480,982 orders/sec | 2,042 ns | 7,083 ns | 14,750 ns |
| Cancel limit order | 3,636,510 orders/sec | 250 ns | 583 ns | 5,334 ns |
| Market order match | 433,576 orders/sec | 2,083 ns | 7,083 ns | 16,375 ns |
| Multi-level market order match | 93,762 orders/sec | 9,291 ns | 18,959 ns | 39,875 ns |

> Ubuntu 22.04 (Docker), Python 3.11, median of 3 runs. Each benchmark isolates a single operation with a pre-populated book to reflect realistic trading conditions. Multi-level market order match walks 5 price levels per submission.
