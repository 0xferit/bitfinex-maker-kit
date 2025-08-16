"""
API client for Bitfinex.

POST_ONLY is explicitly enforced by passing the appropriate flags at the REST
boundary to ensure maker-only execution and to prevent market taking.
"""

from typing import Any

from bfxapi import WSS_HOST, Client  # type: ignore

from ..utilities.constants import POST_ONLY_FLAG, OrderSide, OrderSubmissionError, OrderType


class BitfinexAPIClient:
    """
    API client that handles Bitfinex communication.

    The underlying bitfinex-api-py-postonly library automatically
    enforces POST_ONLY for all limit orders.
    """

    def __init__(self, api_key: str, api_secret: str) -> None:
        """Initialize API client with credentials."""
        self.client = Client(wss_host=WSS_HOST, api_key=api_key, api_secret=api_secret)

    def submit_order(
        self, symbol: str, side: str | OrderSide, amount: float, price: float | None = None
    ) -> Any:
        """
        Submit order with enforced POST_ONLY for limit orders.

        Args:
            symbol: Trading symbol (e.g., "tBTCUSD")
            side: Order side ("buy"/"sell" or OrderSide enum)
            amount: Order amount (positive number)
            price: Price for limit orders, None for market orders

        Returns:
            Order response from Bitfinex API

        Raises:
            OrderSubmissionError: If order submission fails
            ValueError: If parameters are invalid
        """
        # Normalize side
        normalized_side = self._normalize_side(side)

        # Validate parameters
        self._validate_order_params(symbol, normalized_side, amount, price)

        # Convert amount based on side (Bitfinex uses positive for buy, negative for sell)
        bitfinex_amount = amount if normalized_side == OrderSide.BUY else -amount

        # ARCHITECTURAL SAFETY: This program ONLY supports POST_ONLY limit orders
        # Market orders are FORBIDDEN as they take liquidity and violate maker-only strategy
        if price is None:
            raise OrderSubmissionError(
                "Market orders are not supported. This program only supports POST_ONLY limit orders for maker-only trading."
            )

        try:
            # Explicitly enforce POST_ONLY via flags at the API boundary
            return self.client.rest.auth.submit_order(
                type=OrderType.LIMIT.value,
                symbol=symbol,
                amount=bitfinex_amount,
                price=price,
                flags=POST_ONLY_FLAG,
            )
        except Exception as e:
            raise OrderSubmissionError(
                f"Failed to submit {normalized_side.value} order: {e}"
            ) from e

    def get_orders(self) -> list[Any]:
        """Get all active orders."""
        try:
            result = self.client.rest.auth.get_orders()
            # Ensure we always return a list, even if API returns None or other types
            if result is None:
                return []
            elif isinstance(result, list):
                return result
            else:
                # If result is not a list but not None, wrap it in a list
                return [result]
        except Exception as e:
            raise OrderSubmissionError(f"Failed to get orders: {e}") from e

    def cancel_order(self, order_id: int) -> Any:
        """Cancel a single order by ID."""
        try:
            return self.client.rest.auth.cancel_order(id=order_id)
        except Exception as e:
            raise OrderSubmissionError(f"Failed to cancel order {order_id}: {e}") from e

    def cancel_order_multi(self, order_ids: list[int]) -> Any:
        """Cancel multiple orders by IDs."""
        if not order_ids:
            raise ValueError("Order IDs list cannot be empty")

        try:
            return self.client.rest.auth.cancel_order_multi(id=order_ids)
        except Exception as e:
            raise OrderSubmissionError(f"Failed to cancel {len(order_ids)} orders: {e}") from e

    def get_wallets(self) -> Any:
        """Get wallet balances."""
        try:
            return self.client.rest.auth.get_wallets()
        except Exception as e:
            raise OrderSubmissionError(f"Failed to get wallets: {e}") from e

    def get_ticker(self, symbol: str) -> Any:
        """Get ticker data for symbol."""
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty")

        try:
            return self.client.rest.public.get_t_ticker(symbol)
        except Exception as e:
            raise OrderSubmissionError(f"Failed to get ticker for {symbol}: {e}") from e

    def get_trades(self, symbol: str, limit: int = 1) -> Any:
        """Get recent trades for symbol."""
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty")

        if limit <= 0:
            raise ValueError("Limit must be positive")

        try:
            return self.client.rest.public.get_t_trades(symbol, limit=limit)
        except Exception as e:
            raise OrderSubmissionError(f"Failed to get trades for {symbol}: {e}") from e

    def get_orderbook(self, symbol: str, precision: str = "P0") -> Any:
        """Get order book data for symbol."""
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty")

        try:
            # bfxapi uses get_t_book for trading pairs
            return self.client.rest.public.get_t_book(symbol, prec=precision)
        except Exception as e:
            raise OrderSubmissionError(f"Failed to get orderbook for {symbol}: {e}") from e

    def update_order(
        self,
        order_id: int,
        price: float | None = None,
        amount: float | None = None,
        delta: float | None = None,
        use_cancel_recreate: bool = False,
    ) -> Any:
        """Update an order via REST API or fallback to cancel-recreate.

        Note: bfxapi supports authenticated order update; parameters may be strings.
        """
        if order_id <= 0:
            raise ValueError("order_id must be positive")

        try:
            if not use_cancel_recreate and hasattr(self.client.rest.auth, "update_order"):
                kwargs: dict[str, Any] = {"id": order_id}
                if price is not None:
                    kwargs["price"] = price
                if amount is not None:
                    # Preserve side by adjusting sign only when full amount provided; delta handled below
                    kwargs["amount"] = amount
                if delta is not None and hasattr(self.client.rest.auth, "update_order_delta"):
                    # If API supports delta updates, prefer it
                    return self.client.rest.auth.update_order_delta(id=order_id, delta=delta)
                return self.client.rest.auth.update_order(**kwargs)

            # Fallback: cancel and recreate when atomic update not available
            # Fetch existing order, cancel it, then submit a new one
            current = None
            try:
                orders = self.get_orders()
                current = next((o for o in orders if getattr(o, "id", None) == order_id), None)
            except Exception:
                current = None

            # Cancel first
            self.cancel_order(order_id)

            if current is None:
                raise OrderSubmissionError("Original order not found for cancel-recreate")

            symbol = getattr(current, "symbol", None)
            if not isinstance(symbol, str) or not symbol.strip():
                raise OrderSubmissionError("Original order has no valid symbol")
            current_amount = float(getattr(current, "amount", 0.0))
            side = OrderSide.BUY.value if current_amount > 0 else OrderSide.SELL.value

            new_amount = amount if amount is not None else abs(current_amount)
            new_price = price if price is not None else float(getattr(current, "price", 0.0))

            # Submit replacement order with enforced POST_ONLY
            new_order = self.submit_order(
                symbol=str(symbol), side=side, amount=new_amount, price=new_price
            )

            return {
                "status": "SUCCESS",
                "method": "cancel_recreate",
                "original_order_id": order_id,
                "new_order": new_order,
            }
        except Exception as e:
            raise OrderSubmissionError(f"Failed to update order {order_id}: {e}") from e

    @property
    def wss(self) -> Any:
        """Access to WebSocket interface for real-time data."""
        return self.client.wss

    def _normalize_side(self, side: str | OrderSide) -> OrderSide:
        """Normalize order side to OrderSide enum."""
        if isinstance(side, OrderSide):
            return side

        side_str = side.lower().strip()
        if side_str == "buy":
            return OrderSide.BUY
        elif side_str == "sell":
            return OrderSide.SELL
        else:
            raise ValueError(f"Invalid order side: {side}. Must be 'buy' or 'sell'")

    def _validate_order_params(
        self, symbol: str, side: OrderSide, amount: float, price: float | None
    ) -> None:
        """Validate order parameters."""
        if not symbol or not symbol.strip():
            raise ValueError("Symbol cannot be empty")

        if amount <= 0:
            raise ValueError("Amount must be positive")

        # Price is required for limit orders
        if price is None:
            raise ValueError(
                "Price is required. Market orders are not supported - only limit orders."
            )

        if price <= 0:
            raise ValueError("Price must be positive for limit orders")


def create_api_client(api_key: str, api_secret: str) -> BitfinexAPIClient:
    """
    Factory function to create Bitfinex API client.

    Args:
        api_key: Bitfinex API key
        api_secret: Bitfinex API secret

    Returns:
        BitfinexAPIClient instance with POST_ONLY enforcement
    """
    return BitfinexAPIClient(api_key, api_secret)
