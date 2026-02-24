"""
WebSocket streaming for real-time dashboard updates
Streams: status, decisions, positions, orders, events, reconciliation
"""
import asyncio
import json
from typing import Dict, Set
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from packages.shared.logger import logger


class WsStreamMessage:
    """WebSocket stream message"""

    def __init__(
        self,
        msg_type: str,
        data: Dict,
        timestamp: str = None,
    ):
        self.type = msg_type
        self.data = data
        self.timestamp = timestamp or datetime.utcnow().isoformat() + "Z"

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type,
            "timestamp": self.timestamp,
            "data": self.data,
        })


class WsStreamConnection:
    """Represents a single WebSocket connection"""

    def __init__(self, websocket: WebSocket, user_id: str):
        self.websocket = websocket
        self.user_id = user_id
        self.subscribed_streams: Set[str] = set()
        self.created_at = datetime.utcnow()

    async def send(self, message: WsStreamMessage):
        """Send message to client"""
        try:
            await self.websocket.send_text(message.to_json())
        except Exception as e:
            logger.error("ws_send_error", error=str(e))

    def is_subscribed(self, stream: str) -> bool:
        """Check if subscribed to stream"""
        return stream in self.subscribed_streams or "*" in self.subscribed_streams


class WsStreamManager:
    """Manager for WebSocket connections and broadcasting"""

    def __init__(self):
        self.connections: Dict[str, WsStreamConnection] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> WsStreamConnection:
        """Register new connection"""
        await websocket.accept()
        connection = WsStreamConnection(websocket, user_id)
        self.connections[user_id] = connection

        logger.info("ws_client_connected", user_id=user_id, total_connections=len(self.connections))
        return connection

    def disconnect(self, user_id: str):
        """Unregister connection"""
        if user_id in self.connections:
            del self.connections[user_id]
        logger.info("ws_client_disconnected", user_id=user_id, total_connections=len(self.connections))

    async def handle_subscription(
        self,
        user_id: str,
        action: str,
        stream: str,
    ):
        """Handle subscribe/unsubscribe requests"""
        connection = self.connections.get(user_id)
        if not connection:
            return

        if action == "subscribe":
            connection.subscribed_streams.add(stream)
            logger.info("ws_subscribed", user_id=user_id, stream=stream)
        elif action == "unsubscribe":
            connection.subscribed_streams.discard(stream)
            logger.info("ws_unsubscribed", user_id=user_id, stream=stream)

    async def broadcast_status(self, status_data: Dict):
        """Broadcast status updates to all subscribed clients"""
        message = WsStreamMessage("status", status_data)

        tasks = []
        for connection in self.connections.values():
            if connection.is_subscribed("status"):
                tasks.append(connection.send(message))

        if tasks:
            await asyncio.gather(*tasks)

    async def broadcast_decision(self, decision_data: Dict):
        """Broadcast new decision"""
        message = WsStreamMessage("decision", decision_data)

        tasks = []
        for connection in self.connections.values():
            if connection.is_subscribed("decision"):
                tasks.append(connection.send(message))

        if tasks:
            await asyncio.gather(*tasks)

    async def broadcast_position_change(self, position_data: Dict):
        """Broadcast position updates"""
        message = WsStreamMessage("position_change", position_data)

        tasks = []
        for connection in self.connections.values():
            if connection.is_subscribed("positions"):
                tasks.append(connection.send(message))

        if tasks:
            await asyncio.gather(*tasks)

    async def broadcast_order_change(self, order_data: Dict):
        """Broadcast order updates"""
        message = WsStreamMessage("order_change", order_data)

        tasks = []
        for connection in self.connections.values():
            if connection.is_subscribed("orders"):
                tasks.append(connection.send(message))

        if tasks:
            await asyncio.gather(*tasks)

    async def broadcast_event(self, event_data: Dict):
        """Broadcast system event"""
        message = WsStreamMessage("event", event_data)

        tasks = []
        for connection in self.connections.values():
            if connection.is_subscribed("events"):
                tasks.append(connection.send(message))

        if tasks:
            await asyncio.gather(*tasks)

    async def broadcast_recon_summary(self, recon_data: Dict):
        """Broadcast reconciliation summary"""
        message = WsStreamMessage("recon", recon_data)

        tasks = []
        for connection in self.connections.values():
            if connection.is_subscribed("recon"):
                tasks.append(connection.send(message))

        if tasks:
            await asyncio.gather(*tasks)

    async def process_client_message(self, user_id: str, data: Dict):
        """Process incoming client message"""
        action = data.get("action")
        stream = data.get("stream")

        if action in ("subscribe", "unsubscribe"):
            await self.handle_subscription(user_id, action, stream)
            logger.info("ws_subscription_processed", user_id=user_id, action=action, stream=stream)


# Global WebSocket manager
ws_manager = WsStreamManager()
