"""
Base broker interface — all brokers implement this.
Add a new broker: create a new class inheriting BrokerBase.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    action: Literal["buy", "sell"]
    quantity: int
    price: float
    status: str
    is_paper: bool


@dataclass
class Quote:
    symbol: str
    ltp: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    change_pct: float
    timestamp: datetime | None = None


class BrokerBase(ABC):
    """Abstract base for all broker integrations."""

    @abstractmethod
    async def connect(self) -> bool:
        """Authenticate and establish connection."""

    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote:
        """Get live quote for a symbol."""

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        action: Literal["buy", "sell"],
        quantity: int,
        order_type: str = "MARKET",
        price: float | None = None,
    ) -> OrderResult:
        """Place a buy or sell order."""

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""

    @abstractmethod
    async def get_positions(self) -> list[dict]:
        """Get all open positions."""

    @abstractmethod
    async def get_balance(self) -> float:
        """Get available cash balance."""

    @abstractmethod
    async def is_market_open(self) -> bool:
        """Check if market is currently open."""
