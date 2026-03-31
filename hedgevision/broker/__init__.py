"""Broker abstraction layer (local paper + optional CCXT exchange)."""

from hedgevision.broker.router import get_broker

__all__ = ["get_broker"]
