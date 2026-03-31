"""Optional CCXT broker adapter."""

from __future__ import annotations

from typing import Any

from hedgevision.broker.types import BrokerOrder, BrokerPosition, BrokerQuote


def _to_ccxt_symbol(symbol: str) -> str:
    text = symbol.strip().upper()
    if "/" in text:
        return text
    if text.endswith("-USD"):
        base = text[: -len("-USD")]
        return f"{base}/USDT"
    return text.replace("-", "/")


class CCXTBroker:
    backend = "ccxt"

    def __init__(
        self,
        *,
        exchange_id: str = "binance",
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        try:
            import ccxt  # type: ignore
        except Exception as exc:
            raise RuntimeError("CCXT broker requires `ccxt` (pip install ccxt)") from exc

        self.exchange_id = exchange_id
        exchange_cls = getattr(ccxt, exchange_id, None)
        if exchange_cls is None:
            raise RuntimeError(f"Unknown CCXT exchange: {exchange_id}")
        self.exchange = exchange_cls({"enableRateLimit": True})
        if api_key:
            self.exchange.apiKey = api_key
        if api_secret:
            self.exchange.secret = api_secret

    @property
    def exchange_name(self) -> str:
        return self.exchange_id

    def get_quote(self, symbol: str) -> BrokerQuote:
        ccxt_symbol = _to_ccxt_symbol(symbol)
        ticker: dict[str, Any] = self.exchange.fetch_ticker(ccxt_symbol)
        ts = ticker.get("timestamp")
        return BrokerQuote.model_validate(
            {
                "symbol": symbol,
                "backend": self.backend,
                "exchange": self.exchange_name,
                "last": float(ticker["last"]) if ticker.get("last") is not None else None,
                "bid": float(ticker["bid"]) if ticker.get("bid") is not None else None,
                "ask": float(ticker["ask"]) if ticker.get("ask") is not None else None,
                "timestamp_ms": int(ts) if ts is not None else None,
            }
        )

    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float | None = None,
    ) -> BrokerOrder:
        ccxt_symbol = _to_ccxt_symbol(symbol)
        order_type = "limit" if price is not None else "market"
        raw = self.exchange.create_order(ccxt_symbol, order_type, side, quantity, price)
        return BrokerOrder.model_validate(
            {
                "order_id": str(raw.get("id", "")),
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "status": raw.get("status", "open"),
                "backend": self.backend,
                "filled_quantity": float(raw.get("filled") or 0.0),
                "average_fill_price": raw.get("average"),
            }
        )

    def cancel_order(self, order_id: str) -> BrokerOrder:
        raw = self.exchange.cancel_order(order_id)
        symbol = raw.get("symbol", "")
        # Normalise ccxt symbol (BTC/USDT → BTC-USD)
        if "/" in symbol:
            base, quote = symbol.split("/", 1)
            symbol = f"{base}-{'USD' if quote in ('USDT', 'BUSD') else quote}"
        return BrokerOrder.model_validate(
            {
                "order_id": str(raw.get("id", order_id)),
                "symbol": symbol,
                "side": raw.get("side", "buy"),
                "quantity": float(raw.get("amount") or 0.0),
                "price": raw.get("price"),
                "status": "cancelled",
                "backend": self.backend,
                "filled_quantity": float(raw.get("filled") or 0.0),
                "average_fill_price": raw.get("average"),
            }
        )

    def get_open_orders(self) -> list[BrokerOrder]:
        raws = self.exchange.fetch_open_orders() or []
        result = []
        for raw in raws:
            sym = raw.get("symbol", "")
            if "/" in sym:
                base, quote = sym.split("/", 1)
                sym = f"{base}-{'USD' if quote in ('USDT', 'BUSD') else quote}"
            result.append(
                BrokerOrder.model_validate(
                    {
                        "order_id": str(raw.get("id", "")),
                        "symbol": sym,
                        "side": raw.get("side", "buy"),
                        "quantity": float(raw.get("amount") or 0.0),
                        "price": raw.get("price"),
                        "status": raw.get("status", "open"),
                        "backend": self.backend,
                        "filled_quantity": float(raw.get("filled") or 0.0),
                        "average_fill_price": raw.get("average"),
                    }
                )
            )
        return result

    def get_positions(self) -> list[BrokerPosition]:
        raws = self.exchange.fetch_balance() or {}
        positions = []
        total = raws.get("total", {})
        free = raws.get("free", {})
        for asset, qty in total.items():
            if asset in ("USD", "USDT", "BUSD") or not qty:
                continue
            amount = float(qty or 0.0)
            if amount == 0.0:
                continue
            sym = f"{asset}-USD"
            try:
                ticker = self.exchange.fetch_ticker(f"{asset}/USDT")
                current_price: float | None = float(ticker.get("last") or 0.0) or None
            except Exception:
                current_price = None
            positions.append(
                BrokerPosition.model_validate(
                    {
                        "symbol": sym,
                        "quantity": amount,
                        "average_cost": None,
                        "current_price": current_price,
                        "unrealised_pnl": None,
                        "backend": self.backend,
                    }
                )
            )
        return positions
