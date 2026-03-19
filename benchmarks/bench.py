"""
Throughput and latency benchmarks for the matching engine.

Orders are pre-generated before timing starts to isolate the engine's
hot path from object construction overhead. Run inside Docker for
Linux numbers — do not use macOS results in README.
"""

import time, uuid, sys
from pathlib import Path
from typing import List, Optional
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.matching_engine import MatchingEngine
from src.models import Order, OrderSide, OrderType

def generate_orders(n: int, side: Optional[OrderSide] = None, quantity: int = 100) -> List[Order]:
    orders = []
    for i in range(n):
        # if side unspecified, BID/ASK is alternated with overlapping prices to force real matching, not just inserts
        s = side if side is not None else (OrderSide.BID if i % 2 == 0 else OrderSide.ASK)
        price = 100.0 + (i % 20) * 0.25
        orders.append(Order(
            order_id=str(uuid.uuid4()),
            side=s,
            order_type=OrderType.LIMIT,
            price=price,
            quantity=quantity
        ))
    return orders

def bench_limit_insert(n_throughput: int = 1_000_000, n_latency: int = 100_000) -> None:
    # --- Throughput pass ---
    engine = MatchingEngine()
    # all same side — no matching occurs, measures pure insert into SortedDict
    orders = generate_orders(n_throughput, OrderSide.BID)
    start = time.perf_counter_ns()
    for order in orders:
        engine.submit_order(order)
    elapsed = time.perf_counter_ns() - start
    print(f"Throughput : {n_throughput / (elapsed / 1e9):>12,.0f} orders/sec")

    # --- Latency pass ---
    engine = MatchingEngine()
    orders = generate_orders(n_latency, OrderSide.BID)
    latencies = []
    for order in orders:
        t = time.perf_counter_ns()
        engine.submit_order(order)
        latencies.append(time.perf_counter_ns() - t)
    latencies.sort()
    print(f"p50 latency: {latencies[int(n_latency*0.50)]:>12.0f} ns")
    print(f"p99 latency: {latencies[int(n_latency*0.99)]:>12.0f} ns")
    print(f"p999 latency:{latencies[int(n_latency*0.999)]:>12.0f} ns")

def bench_limit_match(n_throughput: int = 1_000_000, n_latency: int = 100_000) -> None:
    # --- Throughput pass ---
    engine = MatchingEngine()
    # pre-populate book with resting asks, every incoming bid matches immediately
    asks = generate_orders(n_throughput, OrderSide.ASK)
    for order in asks:
        engine.submit_order(order)
    bids = generate_orders(n_throughput, OrderSide.BID)
    start = time.perf_counter_ns()
    for order in bids:
        engine.submit_order(order)
    elapsed = time.perf_counter_ns() - start
    print(f"Throughput : {n_throughput / (elapsed / 1e9):>12,.0f} orders/sec")

    # --- Latency pass ---
    engine = MatchingEngine()
    asks = generate_orders(n_latency, OrderSide.ASK)
    for order in asks:
        engine.submit_order(order)
    bids = generate_orders(n_latency, OrderSide.BID)
    latencies = []
    for order in bids:
        t = time.perf_counter_ns()
        engine.submit_order(order)
        latencies.append(time.perf_counter_ns() - t)
    latencies.sort()
    print(f"p50 latency: {latencies[int(n_latency*0.50)]:>12.0f} ns")
    print(f"p99 latency: {latencies[int(n_latency*0.99)]:>12.0f} ns")
    print(f"p999 latency:{latencies[int(n_latency*0.999)]:>12.0f} ns")

def bench_cancel(n_throughput: int = 1_000_000, n_latency: int = 100_000) -> None:
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
    print(f"Throughput : {n_throughput / (elapsed / 1e9):>12,.0f} orders/sec")

    # --- Latency pass ---
    engine = MatchingEngine()
    orders = generate_orders(n_latency, OrderSide.BID)
    for order in orders:
        engine.submit_order(order)
    latencies = []
    for order in orders:
        t = time.perf_counter_ns()
        engine.cancel_order(order.order_id)
        latencies.append(time.perf_counter_ns() - t)
    latencies.sort()
    print(f"p50 latency: {latencies[int(n_latency*0.50)]:>12.0f} ns")
    print(f"p99 latency: {latencies[int(n_latency*0.99)]:>12.0f} ns")
    print(f"p999 latency:{latencies[int(n_latency*0.999)]:>12.0f} ns")

def bench_market_match(n_throughput: int = 1_000_000, n_latency: int = 100_000) -> None:
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
    print(f"Throughput : {n_throughput / (elapsed / 1e9):>12,.0f} orders/sec")

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
    print(f"p50 latency: {latencies[int(n_latency*0.50)]:>12.0f} ns")
    print(f"p99 latency: {latencies[int(n_latency*0.99)]:>12.0f} ns")
    print(f"p999 latency:{latencies[int(n_latency*0.999)]:>12.0f} ns")

def bench_market_multilevel(n_throughput: int = 1_000_000, n_latency: int = 100_000) -> None:
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
    print(f"Throughput : {n_throughput / (elapsed / 1e9):>12,.0f} orders/sec")

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
    print(f"p50 latency: {latencies[int(n_latency*0.50)]:>12.0f} ns")
    print(f"p99 latency: {latencies[int(n_latency*0.99)]:>12.0f} ns")
    print(f"p999 latency:{latencies[int(n_latency*0.999)]:>12.0f} ns")

if __name__ == "__main__":
    print("=" * 40)
    print("Limit order insert")
    print("=" * 40)
    bench_limit_insert()
    print()
    print("=" * 40)
    print("Limit order match")
    print("=" * 40)
    bench_limit_match()
    print()
    print("=" * 40)
    print("Cancel limit order")
    print("=" * 40)
    bench_cancel()
    print()
    print("=" * 40)
    print("Market order match")
    print("=" * 40)
    bench_market_match()
    print()
    print("=" * 40)
    print("Multi-level market order match")
    print("=" * 40)
    bench_market_multilevel()
