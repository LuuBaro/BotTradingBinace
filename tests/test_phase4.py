"""
Phase 4 Testing - Dashboard, WebSocket, Config Versioning
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from apps.api.auth import JWTHandler, DemoUserManager, User
from packages.shared.config_versioning import ConfigVersionManager


class TestJWTAuth:
    """Test JWT authentication"""

    def setup_method(self):
        self.jwt_handler = JWTHandler("test-secret-key")
        self.user = User(
            id="user_123",
            username="testuser",
            role="trader",
        )

    def test_create_access_token(self):
        """Test token creation"""
        token = self.jwt_handler.create_access_token(self.user)
        assert token.access_token
        assert token.token_type == "bearer"
        assert token.expires_in > 0

    def test_decode_valid_token(self):
        """Test decoding valid token"""
        token = self.jwt_handler.create_access_token(self.user)
        payload = self.jwt_handler.decode_token(token.access_token)

        assert payload is not None
        assert payload["username"] == "testuser"
        assert payload["role"] == "trader"

    def test_decode_invalid_token(self):
        """Test decoding invalid token"""
        payload = self.jwt_handler.decode_token("invalid.token.here")
        assert payload is None

    def test_verify_token(self):
        """Test token verification"""
        token = self.jwt_handler.create_access_token(self.user)
        user = self.jwt_handler.verify_token(token.access_token)

        assert user is not None
        assert user.username == "testuser"
        assert user.role == "trader"

    def test_verify_invalid_token(self):
        """Test verifying invalid token"""
        user = self.jwt_handler.verify_token("invalid.token.here")
        assert user is None


class TestUserManager:
    """Test user authentication"""

    def setup_method(self):
        self.user_manager = DemoUserManager()

    def test_get_user(self):
        """Test getting user"""
        user = self.user_manager.get_user("admin")
        assert user is not None
        assert user.username == "admin"
        assert user.role == "admin"

    def test_get_nonexistent_user(self):
        """Test getting nonexistent user"""
        user = self.user_manager.get_user("nonexistent")
        assert user is None

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        result = self.user_manager.verify_password("admin", "admin")
        assert result is True

    def test_verify_password_incorrect(self):
        """Test password verification with wrong password"""
        result = self.user_manager.verify_password("admin", "wrongpassword")
        assert result is False

    def test_verify_password_nonexistent_user(self):
        """Test password verification for nonexistent user"""
        result = self.user_manager.verify_password("nonexistent", "password")
        assert result is False

    def test_demo_users_exist(self):
        """Test that demo users exist"""
        assert self.user_manager.get_user("admin") is not None
        assert self.user_manager.get_user("trader") is not None
        assert self.user_manager.get_user("viewer") is not None

    def test_user_roles(self):
        """Test user roles"""
        admin = self.user_manager.get_user("admin")
        trader = self.user_manager.get_user("trader")
        viewer = self.user_manager.get_user("viewer")

        assert admin.role == "admin"
        assert trader.role == "trader"
        assert viewer.role == "viewer"


class TestConfigVersioning:
    """Test config versioning"""

    @pytest.mark.asyncio
    async def test_create_version(self):
        """Test creating config version"""
        session = AsyncMock()
        manager = ConfigVersionManager(session)

        config = {"max_leverage": 10, "max_position_size": 1.0}

        # Mock the database execute
        with patch.object(session, 'execute', new_callable=AsyncMock) as mock_exec:
            # Mock getting max version number
            mock_result = AsyncMock()
            mock_result.scalar.return_value = 0
            mock_exec.return_value = mock_result

            with patch.object(session, 'commit', new_callable=AsyncMock):
                version = await manager.create_version(
                    config_type="risk",
                    config=config,
                    created_by="test_user",
                    description="Test version",
                )

                assert version.config_type == "risk"
                assert version.config_json == config
                assert version.created_by == "test_user"
                assert version.version_number == 1

    @pytest.mark.asyncio
    async def test_version_numbering(self):
        """Test that versions are numbered sequentially"""
        session = AsyncMock()
        manager = ConfigVersionManager(session)

        # Create first version
        with patch.object(session, 'execute', new_callable=AsyncMock) as mock_exec:
            mock_result = AsyncMock()
            mock_result.scalar.return_value = 0
            mock_exec.return_value = mock_result

            with patch.object(session, 'commit', new_callable=AsyncMock):
                v1 = await manager.create_version(
                    "risk", {"test": 1}, "user1"
                )
                assert v1.version_number == 1

        # Create second version
        with patch.object(session, 'execute', new_callable=AsyncMock) as mock_exec:
            mock_result = AsyncMock()
            mock_result.scalar.return_value = 1
            mock_exec.return_value = mock_result

            with patch.object(session, 'commit', new_callable=AsyncMock):
                v2 = await manager.create_version(
                    "risk", {"test": 2}, "user2"
                )
                assert v2.version_number == 2


class TestWebSocketStreaming:
    """Test WebSocket streaming"""

    def test_ws_message_creation(self):
        """Test WebSocket message creation"""
        from apps.api.websocket import WsStreamMessage

        msg = WsStreamMessage("status", {"uptime": 3600})

        assert msg.type == "status"
        assert msg.data["uptime"] == 3600
        assert msg.timestamp is not None

    def test_ws_message_to_json(self):
        """Test WebSocket message serialization"""
        from apps.api.websocket import WsStreamMessage
        import json

        msg = WsStreamMessage("status", {"uptime": 3600})
        json_str = msg.to_json()
        data = json.loads(json_str)

        assert data["type"] == "status"
        assert data["data"]["uptime"] == 3600
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_ws_manager_connect(self):
        """Test WebSocket manager connection"""
        from apps.api.websocket import WsStreamManager

        manager = WsStreamManager()
        ws = AsyncMock()

        connection = await manager.connect(ws, "user_123")

        assert connection.user_id == "user_123"
        assert "user_123" in manager.connections

    def test_ws_manager_disconnect(self):
        """Test WebSocket manager disconnection"""
        from apps.api.websocket import WsStreamManager, WsStreamConnection

        manager = WsStreamManager()
        ws = AsyncMock()

        # Create mock connection
        connection = WsStreamConnection(ws, "user_123")
        manager.connections["user_123"] = connection

        manager.disconnect("user_123")

        assert "user_123" not in manager.connections

    @pytest.mark.asyncio
    async def test_ws_subscription(self):
        """Test WebSocket subscriptions"""
        from apps.api.websocket import WsStreamManager

        manager = WsStreamManager()
        ws = AsyncMock()

        connection = await manager.connect(ws, "user_123")

        await manager.handle_subscription("user_123", "subscribe", "status")
        assert connection.is_subscribed("status")

        await manager.handle_subscription("user_123", "unsubscribe", "status")
        assert not connection.is_subscribed("status")

    @pytest.mark.asyncio
    async def test_ws_broadcast_status(self):
        """Test broadcasting status updates"""
        from apps.api.websocket import WsStreamManager

        manager = WsStreamManager()
        ws = AsyncMock()

        connection = await manager.connect(ws, "user_123")
        await manager.handle_subscription("user_123", "subscribe", "status")

        await manager.broadcast_status({"uptime": 3600})

        # Verify message was sent
        connection.websocket.send_text.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
