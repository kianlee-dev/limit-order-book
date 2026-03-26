"""
Throughput and latency benchmarks for the matching engine.

Orders are pre-generated before timing starts to isolate the engine's
hot path from object construction overhead. Run inside Docker for
Linux numbers — do not use macOS results in README.
"""

import time, uuid, sys
from pathlib import Path
from typing import List, Optional, Tuple
from statistics import median
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.matching_engine import MatchingEngine
from src.models import Order, OrderSide, OrderType

def generate_orders(n: int, side: Optional[OrderSide] = None, quantity: int = 100, price: float = None) -> List[Order]:
    orders = []
    for i in range(n):
        # if side unspecified, BID/ASK is alternated with overlapping prices to force real matching, not just inserts
        s = side if side is not None else (OrderSide.BID if i % 2 == 0 else OrderSide.ASK)
        p = price if price is not None else (100.0 + (i % 20) * 0.25)
        orders.append(Order(
            order_id=str(uuid.uuid4()),
            side=s,
            order_type=OrderType.LIMIT,
            price=p,
            quantity=quantity
        ))
    return orders

def bench_limit_insert(n_throughput: int = 1_000_000, n_latency: int = 100_000) -> Tuple:
    # warmup
    warmup_engine = MatchingEngine()
    dummies = generate_orders(10_000, OrderSide.BID)
    for d in dummies:
        warmup_engine.submit_order(d)
    # --- Throughput pass ---
    engine = MatchingEngine()
    # all same side — no matching occurs, measures pure insert into SortedDict
    orders = generate_orders(n_throughput, OrderSide.BID)
    start = time.perf_counter_ns()
    for order in orders:
        engine.submit_order(order)
    elapsed = time.perf_counter_ns() - start

    # --- Latency pass ---
    engine = MatchingEngine()
    # pre-populate book to realistic depth — prices outside measured range to avoid deque appends
    for i in range(10_000):
        engine.submit_order(Order(
            order_id=str(uuid.uuid4()),
            side=OrderSide.BID,
            order_type=OrderType.LIMIT,
            price=90.0 + (i % 20) * 0.25,
            quantity=100
        ))
    orders = generate_orders(n_latency, OrderSide.BID)
    latencies = []
    for order in orders:
        t = time.perf_counter_ns()
        engine.submit_order(order)
        latencies.append(time.perf_counter_ns() - t)
    latencies.sort()
    return (
    n_throughput / (elapsed / 1e9),
    latencies[int(n_latency * 0.50)],
    latencies[int(n_latency * 0.99)],
    latencies[int(n_latency * 0.999)]
    )

def bench_limit_match(n_throughput: int = 1_000_000, n_latency: int = 100_000) -> Tuple:
    # warmup
    warmup_engine = MatchingEngine()
    dummy_asks = generate_orders(10_000, OrderSide.ASK)
    for d in dummy_asks:
        warmup_engine.submit_order(d)
    dummy_bids = generate_orders(10_000, OrderSide.BID, price = 105.0)
    for d in dummy_bids:
        warmup_engine.submit_order(d)
    # --- Throughput pass ---
    engine = MatchingEngine()
    # pre-populate book with resting asks, every incoming bid matches immediately
    asks = generate_orders(n_throughput, OrderSide.ASK)
    for order in asks:
        engine.submit_order(order)
    bids = generate_orders(n_throughput, OrderSide.BID, price = 105.0)
    start = time.perf_counter_ns()
    for order in bids:
        engine.submit_order(order)
    elapsed = time.perf_counter_ns() - start

    # --- Latency pass ---
    engine = MatchingEngine()
    asks = generate_orders(n_latency, OrderSide.ASK)
    for order in asks:
        engine.submit_order(order)
    bids = generate_orders(n_latency, OrderSide.BID, price = 105.0)
    latencies = []
    for order in bids:
        t = time.perf_counter_ns()
        engine.submit_order(order)
        latencies.append(time.perf_counter_ns() - t)
    latencies.sort()
    return (
    n_throughput / (elapsed / 1e9),
    latencies[int(n_latency * 0.50)],
    latencies[int(n_latency * 0.99)],
    latencies[int(n_latency * 0.999)]
    )

def bench_cancel(n_throughput: int = 1_000_000, n_latency: int = 100_000) -> Tuple:
    # warmup
    warmup_engine = MatchingEngine()
    dummies = generate_orders(10_000, OrderSide.BID)
    for d in dummies:
        warmup_engine.submit_order(d)
    for d in dummies:
        warmup_engine.cancel_order(d.order_id)
    # --- Throughput pass ---
    engine = MatchingEngine()
    # all same side — orders rest in book, none match, clean cancel targets
    orders = generate_orders(n_throughput, OrderSide.BID)
    for order in orders:
        engine.submit_order(order)
    start = time.perf_counter_ns()
    for order in orders:
        engine.cancel_order(order.order_id)
    elapsed = time.perf_counter_ns() - start

    # --- Latency pass ---
    engine = MatchingEngine()
    # pre-populate book to realistic depth — prices outside cancel range
    for i in range(10_000):
        engine.submit_order(Order(
            order_id=str(uuid.uuid4()),
            side=OrderSide.BID,
            order_type=OrderType.LIMIT,
            price=90.0 + (i % 20) * 0.25,
            quantity=100
        ))
    orders = generate_orders(n_latency, OrderSide.BID)
    for order in orders:
        engine.submit_order(order)
    latencies = []
    for order in orders:
        t = time.perf_counter_ns()
        engine.cancel_order(order.order_id)
        latencies.append(time.perf_counter_ns() - t)
    latencies.sort()
    return (
    n_throughput / (elapsed / 1e9),
    latencies[int(n_latency * 0.50)],
    latencies[int(n_latency * 0.99)],
    latencies[int(n_latency * 0.999)]
    )

def bench_market_match(n_throughput: int = 1_000_000, n_latency: int = 100_000) -> Tuple:
    # warmup
    warmup_engine = MatchingEngine()
    dummy_asks = generate_orders(10_000, OrderSide.ASK, quantity=100)
    for d in dummy_asks:
        warmup_engine.submit_order(d)
    dummy_markets = [Order(
        order_id=str(uuid.uuid4()),
        side=OrderSide.BID,
        order_type=OrderType.MARKET,
        price=None,
        quantity=100
    ) for _ in range(10_000)]
    for d in dummy_markets:
        warmup_engine.submit_order(d)
    # --- Throughput pass ---
    engine = MatchingEngine()
    # 2x resting asks ensures book stays deep throughout — each market order consumes one level of quantity 100
    asks = generate_orders(n_throughput * 2, OrderSide.ASK, quantity=100)
    for order in asks:
        engine.submit_order(order)
    market_orders = [Order(
        order_id=str(uuid.uuid4()),
        side=OrderSide.BID,
        order_type=OrderType.MARKET,
        price=None,
        quantity=100
    ) for _ in range(n_throughput)]
    start = time.perf_counter_ns()
    for order in market_orders:
        engine.submit_order(order)
    elapsed = time.perf_counter_ns() - start

    # --- Latency pass ---
    engine = MatchingEngine()
    asks = generate_orders(n_latency * 2, OrderSide.ASK, quantity=100)
    for order in asks:
        engine.submit_order(order)
    market_orders = [Order(
        order_id=str(uuid.uuid4()),
        side=OrderSide.BID,
        order_type=OrderType.MARKET,
        price=None,
        quantity=100
    ) for _ in range(n_latency)]
    latencies = []
    for order in market_orders:
        t = time.perf_counter_ns()
        engine.submit_order(order)
        latencies.append(time.perf_counter_ns() - t)
    latencies.sort()
    return (
    n_throughput / (elapsed / 1e9),
    latencies[int(n_latency * 0.50)],
    latencies[int(n_latency * 0.99)],
    latencies[int(n_latency * 0.999)]
    )

def bench_market_multilevel(n_throughput: int = 1_000_000, n_latency: int = 100_000) -> Tuple:
    # warmup
    warmup_engine = MatchingEngine()
    dummy_asks = generate_orders(10_000, OrderSide.ASK, quantity=1_000)
    for d in dummy_asks:
        warmup_engine.submit_order(d)
    dummy_markets = [Order(
        order_id=str(uuid.uuid4()),
        side=OrderSide.BID,
        order_type=OrderType.MARKET,
        price=None,
        quantity=5_000
    ) for _ in range(10_000)]
    for d in dummy_markets:
        warmup_engine.submit_order(d)
    # --- Throughput pass ---
    engine = MatchingEngine()
    # 5x resting asks of quantity 1000 — each market order walks 5 price levels per submission
    asks = generate_orders(n_throughput * 5, OrderSide.ASK, quantity=1_000)
    for order in asks:
        engine.submit_order(order)
    market_orders = [Order(
        order_id=str(uuid.uuid4()),
        side=OrderSide.BID,
        order_type=OrderType.MARKET,
        price=None,
        quantity=5_000
    ) for _ in range(n_throughput)]
    start = time.perf_counter_ns()
    for order in market_orders:
        engine.submit_order(order)
    elapsed = time.perf_counter_ns() - start

    # --- Latency pass ---
    engine = MatchingEngine()
    asks = generate_orders(n_latency * 5, OrderSide.ASK, quantity=1_000)
    for order in asks:
        engine.submit_order(order)
    market_orders = [Order(
        order_id=str(uuid.uuid4()),
        side=OrderSide.BID,
        order_type=OrderType.MARKET,
        price=None,
        quantity=5_000
    ) for _ in range(n_latency)]
    latencies = []
    for order in market_orders:
        t = time.perf_counter_ns()
        engine.submit_order(order)
        latencies.append(time.perf_counter_ns() - t)
    latencies.sort()
    return (
    n_throughput / (elapsed / 1e9),
    latencies[int(n_latency * 0.50)],
    latencies[int(n_latency * 0.99)],
    latencies[int(n_latency * 0.999)]
    )

def run_benchmark(name, func, runs=3):
    results = [func() for _ in range(runs)]
    throughput = median(r[0] for r in results)
    throughput_min = min(r[0] for r in results) 
    throughput_max = max(r[0] for r in results)
    p50 = median(r[1] for r in results)
    p99 = median(r[2] for r in results)
    p999 = median(r[3] for r in results)
    p999_min = min(r[3] for r in results)
    p999_max = max(r[3] for r in results)
    print(f"{'=' * 40}")
    print(name)
    print(f"{'=' * 40}")
    print(f"Throughput : {throughput:>12,.0f} orders/sec  (range: {throughput_min:,.0f}–{throughput_max:,.0f})")
    print(f"p50 latency: {p50:>12.0f} ns")
    print(f"p99 latency: {p99:>12.0f} ns")
    print(f"p999 latency:{p999:>12.0f} ns  (range: {p999_min:.0f}–{p999_max:.0f})")
    print()

if __name__ == "__main__":
    run_benchmark("Limit order insert", bench_limit_insert)
    run_benchmark("Limit order match", bench_limit_match)
    run_benchmark("Cancel limit order", bench_cancel)
    run_benchmark("Market order match", bench_market_match)
    run_benchmark("Multi-level market order match", bench_market_multilevel)
