"""
Deprecated: Order updates are handled directly by TradingService via TradingClient.
This module is kept as a thin shim for backwards compatibility only.
"""

from typing import Any

from ..utilities.constants import OrderSubmissionError
from .api_client import BitfinexAPIClient


class OrderUpdateResult:
    """Compatibility shell retained for import stability."""

    def __init__(
        self,
        success: bool,
        method: str,
        order_id: int,
        message: str,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        self.success = success
        self.method = method
        self.order_id = order_id
        self.message = message
        self.response_data = response_data


class OrderUpdateService:
    """Deprecated shim: delegates to API client directly."""

    def __init__(self, api_client: BitfinexAPIClient) -> None:
        self.api_client = api_client

    def update_order(
        self,
        order_id: int,
        price: float | None = None,
        amount: float | None = None,
        delta: float | None = None,
        use_cancel_recreate: bool = False,
    ) -> OrderUpdateResult:
        try:
            result = self.api_client.update_order(
                order_id=order_id,
                price=price,
                amount=amount,
                delta=delta,
                use_cancel_recreate=use_cancel_recreate,
            )
            method = (
                "cancel_recreate" if isinstance(result, dict) and result.get("method") else "direct"
            )
            return OrderUpdateResult(
                True, method, order_id, "OK", result if isinstance(result, dict) else None
            )
        except Exception as e:
            raise OrderSubmissionError(f"Order update failed: {e}") from e

    def get_client(self) -> BitfinexAPIClient:
        """Get the underlying API client."""
        return self.api_client
