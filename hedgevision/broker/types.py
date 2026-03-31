"""Broker type aliases backed by strict Pydantic schemas."""

from hedgevision.models import BrokerOrderPayload, BrokerPositionPayload, BrokerQuotePayload

BrokerQuote = BrokerQuotePayload
BrokerOrder = BrokerOrderPayload
BrokerPosition = BrokerPositionPayload

__all__ = ["BrokerQuote", "BrokerOrder", "BrokerPosition"]

