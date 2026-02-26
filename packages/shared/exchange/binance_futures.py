"""
Binance Futures Adapter - REST API Client
Handles signed requests, server time sync, and all Futures endpoints
"""
import hashlib
import hmac
import time
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode
import aiohttp
from packages.shared.config import settings
from packages.shared.logger import logger
from packages.shared.enums import Side, OrderType, OrderStatus


class BinanceFuturesClient:
    """
    Async Binance Futures API client
    Supports both testnet and production
    """

    def __init__(self):
        self.api_key = settings.binance_api_key
        self.api_secret = settings.binance_api_secret
        
        # Base URL from settings or auto-select based on testnet flag
        if settings.binance_base_url:
            self.base_url = settings.binance_base_url
        elif settings.binance_testnet:
            self.base_url = "https://testnet.binancefuture.com"
        else:
            self.base_url = "https://fapi.binance.com"
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.server_time_offset = 0  # Local - Server time diff
        
        logger.info(
            "binance_client_initialized",
            testnet=settings.binance_testnet,
            base_url=self.base_url,
        )

    async def __aenter__(self):
        """Async context manager entry"""
        # Force ThreadedResolver to avoid DNS issues with aiodns on Windows
        connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
        self.session = aiohttp.ClientSession(connector=connector)
        await self.sync_server_time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def sync_server_time(self) -> None:
        """Sync local time with Binance server time to prevent timestamp errors"""
        try:
            before = int(time.time() * 1000)
            server_time = await self._request("GET", "/fapi/v1/time", signed=False)
            after = int(time.time() * 1000)
            
            # Calculate offset (server time - local time)
            server_ts = server_time["serverTime"]
            local_ts = (before + after) // 2
            self.server_time_offset = server_ts - local_ts
            
            logger.info(
                "server_time_synced",
                offset_ms=self.server_time_offset,
                local=local_ts,
                server=server_ts,
            )
        except Exception as e:
            logger.error("server_time_sync_failed", error=str(e))
            self.server_time_offset = 0

    def _get_timestamp(self) -> int:
        """Get current timestamp adjusted for server time offset"""
        return int(time.time() * 1000) + self.server_time_offset

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate HMAC SHA256 signature for signed requests"""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Binance API
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint
            params: Query/body parameters
            signed: Whether request needs signature
        
        Returns:
            Response JSON
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        params = params or {}
        
        # Add timestamp and signature for signed requests
        if signed:
            params["timestamp"] = self._get_timestamp()
            params["signature"] = self._generate_signature(params)
        
        headers = {
            "X-MBX-APIKEY": self.api_key,
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                async with self.session.get(url, params=params, headers=headers) as response:
                    if response.status >= 400:
                        body = await response.text()
                        logger.error("binance_error_response", status=response.status, body=body, endpoint=endpoint)
                    response.raise_for_status()
                    return await response.json()
            
            elif method == "POST":
                async with self.session.post(url, params=params, headers=headers) as response:
                    if response.status >= 400:
                        body = await response.text()
                        logger.error("binance_error_response", status=response.status, body=body, endpoint=endpoint)
                    response.raise_for_status()
                    return await response.json()
            
            elif method == "DELETE":
                async with self.session.delete(url, params=params, headers=headers) as response:
                    if response.status >= 400:
                        body = await response.text()
                        logger.error("binance_error_response", status=response.status, body=body, endpoint=endpoint)
                    response.raise_for_status()
                    return await response.json()
            
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        
        except aiohttp.ClientResponseError as e:
            # Handle 400 Bad Request with more detail if possible
            if e.status == 400:
                try:
                    # In higher versions of aiohttp, we might not have access to the body here
                    # unless we read it before raise_for_status. 
                    # Let's try to capture it.
                    pass
                except:
                    pass
            logger.error(
                "binance_api_error",
                method=method,
                endpoint=endpoint,
                status=e.status,
                message=e.message,
                url=str(e.request_info.url) if e.request_info else None
            )
            raise
        except Exception as e:
            logger.error(
                "binance_request_failed",
                method=method,
                endpoint=endpoint,
                error=str(e),
            )
            raise

    # === Account endpoints ===

    async def get_account_balance(self) -> List[Dict[str, Any]]:
        """Get futures account balance"""
        result = await self._request("GET", "/fapi/v2/balance", signed=True)
        return result

    async def get_balance(self) -> Dict[str, Any]:
        """Get balance in uniform format compatible with MockExchange"""
        try:
            account_info = await self.get_account_info()
            # Extract wallet balance from account info
            total_wallet_balance = account_info.get("totalWalletBalance", 0)
            available_balance = account_info.get("availableBalance", 0)
            
            return {
                "balance": float(available_balance),
                "wallet_balance": float(total_wallet_balance),
            }
        except Exception as e:
            logger.error("get_balance_failed", error=str(e))
            return {"balance": 0, "wallet_balance": 0}

    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information including positions"""
        result = await self._request("GET", "/fapi/v2/account", signed=True)
        return result

    async def get_position_risk(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get position risk information"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        result = await self._request("GET", "/fapi/v2/positionRisk", params=params, signed=True)
        return result

    # === Order endpoints ===

    async def place_order(
        self,
        symbol: str,
        side: Side,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        reduce_only: bool = False,
        time_in_force: str = "GTC",
        client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Place a new order
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            side: BUY or SELL
            order_type: MARKET, LIMIT, STOP_MARKET, TAKE_PROFIT_MARKET
            quantity: Order quantity
            price: Limit price (required for LIMIT orders)
            stop_price: Stop price (required for STOP/TP orders)
            reduce_only: Reduce-only flag
            time_in_force: GTC, IOC, FOK
            client_order_id: Client order ID for idempotency
        
        Returns:
            Order response
        """
        params = {
            "symbol": symbol,
            "side": "BUY" if side == Side.LONG else "SELL",
            "type": self._convert_order_type(order_type),
            "quantity": quantity,
        }
        
        if price and order_type == OrderType.LIMIT:
            params["price"] = price
            params["timeInForce"] = time_in_force
        
        if stop_price and order_type in [OrderType.STOP_MARKET, OrderType.TAKE_PROFIT_MARKET]:
            params["stopPrice"] = stop_price
        
        if reduce_only:
            params["reduceOnly"] = "true"
        
        if client_order_id:
            params["newClientOrderId"] = client_order_id
        
        result = await self._request("POST", "/fapi/v1/order", params=params, signed=True)
        
        logger.info(
            "binance_order_placed",
            symbol=symbol,
            side=side.value,
            type=order_type.value,
            quantity=quantity,
            order_id=result.get("orderId"),
        )
        
        return result

    async def cancel_order(
        self,
        symbol: str,
        order_id: Optional[int] = None,
        client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cancel an order"""
        params = {"symbol": symbol}
        
        if order_id:
            params["orderId"] = order_id
        elif client_order_id:
            params["origClientOrderId"] = client_order_id
        else:
            raise ValueError("Either order_id or client_order_id must be provided")
        
        result = await self._request("DELETE", "/fapi/v1/order", params=params, signed=True)
        
        logger.info(
            "binance_order_cancelled",
            symbol=symbol,
            order_id=order_id or result.get("orderId"),
        )
        
        return result

    async def get_order(
        self,
        symbol: str,
        order_id: Optional[int] = None,
        client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get order status"""
        params = {"symbol": symbol}
        
        if order_id:
            params["orderId"] = order_id
        elif client_order_id:
            params["origClientOrderId"] = client_order_id
        else:
            raise ValueError("Either order_id or client_order_id must be provided")
        
        result = await self._request("GET", "/fapi/v1/order", params=params, signed=True)
        return result

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all open orders"""
        params = {}
        if symbol:
            params["symbol"] = symbol
        result = await self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)
        return result

    async def get_all_orders(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all orders (active, canceled, filled) for a symbol"""
        params = {"symbol": symbol, "limit": limit}
        result = await self._request("GET", "/fapi/v1/allOrders", params=params, signed=True)
        return result

    # === Market data endpoints ===

    async def get_ticker_price(self, symbol: str) -> Dict[str, Any]:
        """Get latest price for symbol"""
        params = {"symbol": symbol}
        result = await self._request("GET", "/fapi/v1/ticker/price", params=params, signed=False)
        return result

    async def get_mark_price(self, symbol: str) -> Dict[str, Any]:
        """Get mark price for symbol"""
        params = {"symbol": symbol}
        result = await self._request("GET", "/fapi/v1/premiumIndex", params=params, signed=False)
        return result

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 100,
    ) -> List[List[Any]]:
        """Get kline/candlestick data"""
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        result = await self._request("GET", "/fapi/v1/klines", params=params, signed=False)
        return result

    async def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """Set leverage for symbol"""
        params = {
            "symbol": symbol,
            "leverage": leverage,
        }
        result = await self._request("POST", "/fapi/v1/leverage", params=params, signed=True)
        
        logger.info(
            "binance_leverage_set",
            symbol=symbol,
            leverage=leverage,
        )
        
        return result

    async def set_margin_type(self, symbol: str, margin_type: str = "CROSSED") -> Dict[str, Any]:
        """Set margin type (CROSSED or ISOLATED)"""
        params = {
            "symbol": symbol,
            "marginType": margin_type,
        }
        try:
            result = await self._request("POST", "/fapi/v1/marginType", params=params, signed=True)
            return result
        except aiohttp.ClientResponseError as e:
            # Ignore error if margin type is already set
            if e.status == 400 and "No need to change margin type" in str(e):
                logger.debug("margin_type_already_set", symbol=symbol, margin_type=margin_type)
                return {"msg": "No change needed"}
            raise

    async def get_exchange_info(self) -> Dict[str, Any]:
        """Get exchange information including symbol rules"""
        result = await self._request("GET", "/fapi/v1/exchangeInfo", signed=False)
        return result

    async def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get information for a specific symbol"""
        info = await self.get_exchange_info()
        for s in info["symbols"]:
            if s["symbol"] == symbol:
                return s
        return None

    def round_quantity(self, symbol_info: Dict[str, Any], quantity: float) -> float:
        """Round quantity according to LOT_SIZE filter"""
        lot_size_filter = next(f for f in symbol_info["filters"] if f["filterType"] == "LOT_SIZE")
        step_size = float(lot_size_filter["stepSize"])
        precision = 0
        if step_size < 1:
            # Safely handle step_size without decimal point
            if "." in lot_size_filter["stepSize"]:
                precision = len(lot_size_filter["stepSize"].split(".")[1].rstrip("0"))
            else:
                precision = 0
        
        # Use decimal formatting to avoid floating point issues if needed, 
        # but round() is usually fine for Binance
        rounded = round(quantity, precision)
        if rounded == 0 and quantity > 0:
            return step_size
        return rounded

    def round_price(self, symbol_info: Dict[str, Any], price: float) -> float:
        """Round price according to PRICE_FILTER"""
        price_filter = next(f for f in symbol_info["filters"] if f["filterType"] == "PRICE_FILTER")
        tick_size = float(price_filter["tickSize"])
        if "." in price_filter["tickSize"]:
            precision = len(price_filter["tickSize"].split(".")[1].rstrip("0"))
        else:
            precision = 0
        return round(price, precision)

    # === Helper methods ===

    def _convert_order_type(self, order_type: OrderType) -> str:
        """Convert internal OrderType to Binance API type"""
        mapping = {
            OrderType.MARKET: "MARKET",
            OrderType.LIMIT: "LIMIT",
            OrderType.STOP_MARKET: "STOP_MARKET",
            OrderType.TAKE_PROFIT_MARKET: "TAKE_PROFIT_MARKET",
        }
        return mapping.get(order_type, "MARKET")

    def _convert_order_status(self, binance_status: str) -> OrderStatus:
        """Convert Binance order status to internal status"""
        mapping = {
            "NEW": OrderStatus.NEW,
            "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELED,
            "REJECTED": OrderStatus.REJECTED,
            "EXPIRED": OrderStatus.EXPIRED,
        }
        return mapping.get(binance_status, OrderStatus.FAILED)


# Singleton instance
_binance_client: Optional[BinanceFuturesClient] = None


async def get_binance_client() -> BinanceFuturesClient:
    """Get or create Binance client instance"""
    global _binance_client
    if _binance_client is None:
        _binance_client = BinanceFuturesClient()
    return _binance_client
