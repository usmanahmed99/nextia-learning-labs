"""Read-only access to Larkfield's orders (data/orders.sqlite, synthetic)."""

import sqlite3
from pathlib import Path

from .data import ORDERS_DB


class OrderBook:
    """Read-only access to orders.sqlite."""

    def __init__(self, path: Path = ORDERS_DB):
        self.path = path

    def find(self, order_id: str) -> dict | None:
        con = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)  # read-only connection
        con.row_factory = sqlite3.Row
        try:
            order = con.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
            if order is None:
                return None
            items = con.execute("SELECT product, quantity, unit_price FROM order_items WHERE order_id = ? "
                                "ORDER BY product", (order_id,)).fetchall()
        finally:
            con.close()
        return {**dict(order), "items": [dict(i) for i in items]}
