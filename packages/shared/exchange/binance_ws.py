"""
Binance Futures WebSocket Client
Handles real-time market data streams with automatic reconnection
"""
import asyncio
import json
from typing import Dict, Set, Callable, Any, Optional
import aiohttp
from packages.shared.config import settings
from packages.shared.logger import logger


class BinanceFuturesWebSocket:
    """
    Async WebSocket client for Binance Futures
    Supports automatic reconnection and multiple stream subscriptions
    """

    def __init__(self):
        # WebSocket URL based on testnet flag
        if settings.binance_testnet:
            self.ws_url = "wss://stream.binancefuture.com/ws"
        else:
            self.ws_url = "wss://fstream.binance.com/ws"
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        
        # Stream subscriptions and callbacks
        self.streams: Set[str] = set()
        self.callbacks: Dict[str, Callable] = {}
        
        # Connection state
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5  # seconds
        
        # Background tasks
        self.listen_task: Optional[asyncio.Task] = None
        self.ping_task: Optional[asyncio.Task] = None
        
        logger.info(
            "binance_ws_initialized",
            ws_url=self.ws_url,
            testnet=settings.binance_testnet,
        )

    async def connect(self) -> None:
        """Establish WebSocket connection"""
        if self.is_connected:
            return
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Construct stream URL
            if self.streams:
                streams = "/".join(self.streams)
                url = f"{self.ws_url}/{streams}"
            else:
                url = self.ws_url
            
            self.ws = await self.session.ws_connect(url)
            self.is_connected = True
            self.reconnect_attempts = 0
            
            logger.info(
                "binance_ws_connected",
                url=url,
                streams=list(self.streams),
            )
            
            # Start background tasks
            self.listen_task = asyncio.create_task(self._listen())
            self.ping_task = asyncio.create_task(self._ping_loop())
        
        except Exception as e:
            logger.error("binance_ws_connect_failed", error=str(e))
            await self._handle_reconnect()

    async def disconnect(self) -> None:
        """Close WebSocket connection"""
        self.is_connected = False
        
        # Cancel background tasks
        if self.listen_task:
            self.listen_task.cancel()
        if self.ping_task:
            self.ping_task.cancel()
        
        # Close WebSocket
        if self.ws:
            await self.ws.close()
            self.ws = None
        
        # Close session
        if self.session:
            await self.session.close()
            self.session = None
        
        logger.info("binance_ws_disconnected")

    async def subscribe(
        self,
        stream: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """
        Subscribe to a stream
        
        Args:
            stream: Stream name (e.g., btcusdt@kline_1m, btcusdt@markPrice)
            callback: Async function to call when message received
        
        Examples:
            await ws.subscribe("btcusdt@kline_1m", on_kline)
            await ws.subscribe("btcusdt@markPrice", on_mark_price)
        """
        self.streams.add(stream)
        self.callbacks[stream] = callback
        
        logger.info("binance_ws_subscribed", stream=stream)
        
        # Reconnect with new stream if already connected
        if self.is_connected:
            await self.disconnect()
            await self.connect()

    async def unsubscribe(self, stream: str) -> None:
        """Unsubscribe from a stream"""
        self.streams.discard(stream)
        self.callbacks.pop(stream, None)
        
        logger.info("binance_ws_unsubscribed", stream=stream)

    async def _listen(self) -> None:
        """Listen for incoming WebSocket messages"""
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_message(msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error("binance_ws_error", error=self.ws.exception())
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.warning("binance_ws_closed")
                    break
        except asyncio.CancelledError:
            logger.debug("binance_ws_listen_cancelled")
        except Exception as e:
            logger.error("binance_ws_listen_error", error=str(e))
        finally:
            await self._handle_reconnect()

    async def _handle_message(self, data: str) -> None:
        """Handle incoming WebSocket message"""
        try:
            msg = json.loads(data)
            
            # Extract stream name from combined stream format
            stream = msg.get("stream")
            if not stream:
                # Single stream format
                stream = msg.get("e")  # Event type
            
            # Route to appropriate callback
            for subscribed_stream, callback in self.callbacks.items():
                if stream and subscribed_stream in stream:
                    await callback(msg)
                    break
        
        except json.JSONDecodeError as e:
            logger.error("binance_ws_json_error", error=str(e), data=data)
        except Exception as e:
            logger.error("binance_ws_message_error", error=str(e))

    async def _ping_loop(self) -> None:
        """Send periodic ping to keep connection alive"""
        try:
            while self.is_connected:
                await asyncio.sleep(30)  # Ping every 30 seconds
                if self.ws and not self.ws.closed:
                    await self.ws.ping()
        except asyncio.CancelledError:
            logger.debug("binance_ws_ping_cancelled")
        except Exception as e:
            logger.error("binance_ws_ping_error", error=str(e))

    async def _handle_reconnect(self) -> None:
        """Handle reconnection logic"""
        if not self.is_connected:
            return
        
        self.is_connected = False
        
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(
                "binance_ws_max_reconnects_reached",
                attempts=self.reconnect_attempts,
            )
            return
        
        self.reconnect_attempts += 1
        await asyncio.sleep(self.reconnect_delay)
        
        logger.info(
            "binance_ws_reconnecting",
            attempt=self.reconnect_attempts,
            max_attempts=self.max_reconnect_attempts,
        )
        
        await self.connect()


# Singleton instance
_binance_ws: Optional[BinanceFuturesWebSocket] = None


async def get_binance_ws() -> BinanceFuturesWebSocket:
    """Get or create Binance WebSocket instance"""
    global _binance_ws
    if _binance_ws is None:
        _binance_ws = BinanceFuturesWebSocket()
    return _binance_ws


# === Helper functions for common streams ===

async def subscribe_kline(
    symbol: str,
    interval: str,
    callback: Callable[[Dict[str, Any]], None],
) -> None:
    """
    Subscribe to kline/candlestick stream
    
    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        interval: Kline interval (1m, 5m, 15m, 1h, etc.)
        callback: Async function to call when kline received
    """
    ws = await get_binance_ws()
    stream = f"{symbol.lower()}@kline_{interval}"
    await ws.subscribe(stream, callback)


async def subscribe_mark_price(
    symbol: str,
    callback: Callable[[Dict[str, Any]], None],
    update_speed: str = "1s",
) -> None:
    """
    Subscribe to mark price stream
    
    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        callback: Async function to call when mark price received
        update_speed: Update speed (1s or 3s)
    """
    ws = await get_binance_ws()
    stream = f"{symbol.lower()}@markPrice@{update_speed}"
    await ws.subscribe(stream, callback)


async def subscribe_ticker(
    symbol: str,
    callback: Callable[[Dict[str, Any]], None],
) -> None:
    """
    Subscribe to 24hr ticker stream
    
    Args:
        symbol: Trading pair (e.g., BTCUSDT)
        callback: Async function to call when ticker received
    """
    ws = await get_binance_ws()
    stream = f"{symbol.lower()}@ticker"
    await ws.subscribe(stream, callback)
