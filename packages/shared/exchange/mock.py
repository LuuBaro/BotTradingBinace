"""
Mock Exchange for testing without live API
Simulates order execution with configurable latency
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List
from packages.shared.config import settings
from packages.shared.enums import OrderStatus, Side, OrderType
from packages.shared.logger import logger


class MockOrder:
    """Mock order object"""

    def __init__(
        self,
        order_id: str,
        client_order_id: str,
        symbol: str,
        side: Side,
        order_type: OrderType,
        quantity: float,
        price: float | None = None,
    ):
        self.order_id = order_id
        self.client_order_id = client_order_id
        self.symbol = symbol
        self.side = side
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.filled_qty = 0.0
        self.avg_price = 0.0
        self.status = OrderStatus.NEW
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "filled_qty": self.filled_qty,
            "avg_price": self.avg_price,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class MockExchange:
    """
    Mock exchange that simulates Binance Futures behavior
    For testing without actual API calls
    """

    def __init__(self):
        self.balance = settings.mock_initial_balance
        self.orders: Dict[str, MockOrder] = {}
        self.positions: Dict[str, dict] = {}
        self.fill_latency_ms = settings.mock_fill_latency_ms
        logger.info("mock_exchange_initialized", balance=self.balance)

    async def place_order(
        self,
        symbol: str,
        side: Side,
        order_type: OrderType,
        quantity: float,
        price: float | None = None,
        client_order_id: str | None = None,
        stop_price: float | None = None,
    ) -> dict:
        """
        Place a mock order
        Returns immediately with order_id, but fills after latency
        """
        order_id = f"MOCK_{uuid.uuid4().hex[:16].upper()}"
        client_order_id = client_order_id or f"CLIENT_{uuid.uuid4().hex[:16]}"

        order = MockOrder(
            order_id=order_id,
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
        )

        self.orders[order_id] = order

        logger.info(
            "mock_order_placed",
            order_id=order_id,
            symbol=symbol,
            side=side.value,
            quantity=quantity,
        )

        # Auto-fill after latency (simulate market execution)
        if order_type == OrderType.MARKET:
            asyncio.create_task(self._auto_fill_order(order_id, price or 50000.0))

        return order.to_dict()

    async def _auto_fill_order(self, order_id: str, fill_price: float) -> None:
        """Auto-fill order after latency"""
        await asyncio.sleep(self.fill_latency_ms / 1000.0)

        if order_id in self.orders:
            order = self.orders[order_id]
            order.filled_qty = order.quantity
            order.avg_price = fill_price
            order.status = OrderStatus.FILLED
            order.updated_at = datetime.utcnow()

            # Update position
            await self._update_position(order)

            logger.info(
                "mock_order_filled",
                order_id=order_id,
                filled_qty=order.filled_qty,
                avg_price=fill_price,
            )

    async def _update_position(self, order: MockOrder) -> None:
        """Update position after order fill"""
        symbol = order.symbol

        if symbol not in self.positions:
            # New position
            self.positions[symbol] = {
                "symbol": symbol,
                "side": order.side.value,
                "qty": order.filled_qty if order.side == Side.LONG else -order.filled_qty,
                "entry_price": order.avg_price,
                "unrealized_pnl": 0.0,
            }
        else:
            # Update existing position
            pos = self.positions[symbol]
            current_qty = pos["qty"]
            new_qty = order.filled_qty if order.side == Side.LONG else -order.filled_qty

            # Close or reverse position
            if (current_qty > 0 and new_qty < 0) or (current_qty < 0 and new_qty > 0):
                # Opposite direction - close/reverse
                if abs(new_qty) >= abs(current_qty):
                    # Full close or reverse
                    del self.positions[symbol]
                else:
                    # Partial close
                    pos["qty"] += new_qty
            else:
                # Same direction - add to position
                total_qty = abs(current_qty) + abs(new_qty)
                # Weighted average entry price
                pos["entry_price"] = (
                    pos["entry_price"] * abs(current_qty) + order.avg_price * abs(new_qty)
                ) / total_qty
                pos["qty"] += new_qty

    async def get_order(self, order_id: str) -> dict:
        """Get order status"""
        if order_id not in self.orders:
            raise ValueError(f"Order {order_id} not found")

        return self.orders[order_id].to_dict()

    async def get_order_by_client_id(self, client_order_id: str) -> dict | None:
        """Get order by client order ID"""
        for order in self.orders.values():
            if order.client_order_id == client_order_id:
                return order.to_dict()
        return None

    async def get_position(self, symbol: str) -> dict | None:
        """Get position for symbol"""
        return self.positions.get(symbol)

    async def get_all_positions(self) -> List[dict]:
        """Get all positions"""
        return list(self.positions.values())

    async def get_balance(self) -> dict:
        """Get account balance"""
        return {
            "asset": "USDT",
            "balance": self.balance,
            "wallet_balance": self.balance,
            "available": self.balance,
        }

    async def cancel_order(self, order_id: str) -> dict:
        """Cancel an order"""
        if order_id not in self.orders:
            raise ValueError(f"Order {order_id} not found")

        order = self.orders[order_id]
        if order.status == OrderStatus.FILLED:
            raise ValueError("Cannot cancel filled order")

        order.status = OrderStatus.CANCELED
        order.updated_at = datetime.utcnow()

        logger.info("mock_order_canceled", order_id=order_id)
        return order.to_dict()

    def get_mark_price(self, symbol: str) -> float:
        """Get mock mark price (for testing)"""
        # Mock prices for common symbols
        mock_prices = {
            "BTCUSDT": 50000.0,
            "ETHUSDT": 3000.0,
            "BNBUSDT": 400.0,
        }
        return mock_prices.get(symbol, 1000.0)
