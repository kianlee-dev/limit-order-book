import csv, sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.matching_engine import MatchingEngine
from src.models import Order, OrderSide, OrderType

def replay(filepath: str):
    """
    Demonstrates core matching engine behaviour:
    T=1000-1002: limit vs limit partial fill, market order on empty book
    T=1003-1005: limit order walking price levels, IOC resting ask
    T=1006:      IOC partial fill — remainder cancelled
    T=1007:      FOK killed — insufficient liquidity
    T=1008-1010: three ask levels added to book
    T=1011:      market order walking three price levels
    """
    engine = MatchingEngine()
    engine.on_fill(lambda f: print(f" FILL: {f.aggressor_order_id} x {f.passive_order_id} " f"@ {f.price} qty={f.quantity} time = {datetime.utcfromtimestamp(f.timestamp / 1e9).strftime('%H:%M:%S.%f')}"))

    with open(filepath) as f:
        for row in csv.DictReader(f):
            order = Order(
            order_id=row['order_id'],
            side=OrderSide.BID if row['side'] == 'bid' else OrderSide.ASK,
            order_type=OrderType.LIMIT if row['type'] == 'limit' else OrderType.MARKET,
            price=float(row['price']) if row['price'] else None,
            quantity=int(row['quantity']),
            ioc = row['ioc'] == 'true',
            fok = row['fok'] == 'true'
            )

            print(f"[T={row['timestamp']}] {row['side'].upper()} {row['type']}"
                f" qty={row['quantity']}"
                + (f" @ {row['price']}" if row['price'] else "")
                + (" [IOC]" if row['ioc'] == 'true' else "")
                + (" [FOK]" if row['fok'] == 'true' else ""))
            engine.submit_order(order)
            bids, asks = engine.book.depth(3)
            print(f" BID: {bids}")
            print(f" ASK: {asks}")

if __name__ == "__main__":
    replay("examples/sample_orders.csv")