"""Ports implemented by outer adapters."""

from paper_trading.application.ports.market_data import MarketDataPort
from paper_trading.application.ports.paper_exchange import PaperExchange

__all__ = ["MarketDataPort", "PaperExchange"]
