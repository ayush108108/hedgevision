"""Local paper broker backed by public market data."""

from __future__ import annotations

import uuid
from typing import Any

from hedgevision.broker.types import BrokerOrder, BrokerPosition, BrokerQuote


class PaperBroker:
    """Simulated local broker that never places real orders.

    Maintains in-memory state for orders and positions across a session.
    Fill prices are sourced from live yfinance quotes for market orders.
    """

    backend = "paper"
    exchange = "paper"

    def __init__(self) -> None:
        self._orders: dict[str, dict[str, Any]] = {}
        self._positions: dict[str, dict[str, Any]] = {}

    def get_quote(self, symbol: str) -> BrokerQuote:
        try:
            import yfinance as yf
        except Exception as exc:
            raise RuntimeError("Paper broker requires `yfinance` (pip install yfinance)") from exc

        ticker = yf.Ticker(symbol)
        info: dict[str, Any] = {}
        try:
            fast = ticker.fast_info or {}
            if isinstance(fast, dict):
                info.update(fast)
        except Exception:
            pass
        try:
            full = ticker.info or {}
            if isinstance(full, dict):
                info.update(full)
        except Exception:
            pass

        last = info.get("lastPrice") or info.get("regularMarketPrice") or info.get("currentPrice")
        bid = info.get("bid")
        ask = info.get("ask")
        timestamp_ms = info.get("lastTradeDate")
        try:
            ts = int(timestamp_ms.timestamp() * 1000) if timestamp_ms is not None else None
        except Exception:
            ts = None

        return BrokerQuote.model_validate(
            {
                "symbol": symbol,
                "backend": self.backend,
                "exchange": self.exchange,
                "last": float(last) if last is not None else None,
                "bid": float(bid) if bid is not None else None,
                "ask": float(ask) if ask is not None else None,
                "timestamp_ms": ts,
            }
        )

    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float | None = None,
    ) -> BrokerOrder:
        """Simulate placing an order.  Paper orders are filled immediately."""
        order_id = str(uuid.uuid4())
        try:
            quote = self.get_quote(symbol)
            fill_price: float | None = price if price is not None else quote.last
        except Exception:
            fill_price = price

        order = BrokerOrder.model_validate(
            {
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "status": "filled",
                "backend": self.backend,
                "filled_quantity": quantity,
                "average_fill_price": fill_price,
            }
        )
        self._orders[order_id] = order.model_dump()

        # Update in-memory position
        pos = self._positions.setdefault(
            symbol, {"symbol": symbol, "quantity": 0.0, "average_cost": None}
        )
        if side == "buy":
            old_qty = pos["quantity"]
            old_cost = pos["average_cost"] or (fill_price or 0.0)
            new_qty = old_qty + quantity
            if fill_price is not None and new_qty != 0:
                pos["average_cost"] = (old_qty * old_cost + quantity * fill_price) / new_qty
            pos["quantity"] = new_qty
        elif side == "sell":
            pos["quantity"] = pos["quantity"] - quantity

        return order

    def cancel_order(self, order_id: str) -> BrokerOrder:
        """Cancel an open order (no-op for already-filled paper orders)."""
        raw = self._orders.get(order_id)
        if raw is None:
            raise KeyError(f"Order {order_id!r} not found")
        if raw["status"] == "open":
            raw["status"] = "cancelled"
            self._orders[order_id] = raw
        return BrokerOrder.model_validate(raw)

    def get_open_orders(self) -> list[BrokerOrder]:
        """Return all open (unfilled) orders."""
        return [
            BrokerOrder.model_validate(o)
            for o in self._orders.values()
            if o["status"] == "open"
        ]

    def get_positions(self) -> list[BrokerPosition]:
        """Return current in-memory positions (non-zero quantity only)."""
        positions = []
        for sym, pos in self._positions.items():
            if pos["quantity"] == 0.0:
                continue
            try:
                quote = self.get_quote(sym)
                current_price: float | None = quote.last
            except Exception:
                current_price = None

            avg_cost = pos["average_cost"]
            unrealised: float | None = None
            if current_price is not None and avg_cost is not None:
                unrealised = (current_price - avg_cost) * pos["quantity"]

            positions.append(
                BrokerPosition.model_validate(
                    {
                        "symbol": sym,
                        "quantity": pos["quantity"],
                        "average_cost": avg_cost,
                        "current_price": current_price,
                        "unrealised_pnl": unrealised,
                        "backend": self.backend,
                    }
                )
            )
        return positions
