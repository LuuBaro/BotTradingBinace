"""
RBAC (Role-Based Access Control) system for Telegram bot
Manages user roles and permissions
"""
from enum import Enum
from datetime import datetime
from typing import Dict, Set


class UserRole(str, Enum):
    """User roles in the system"""
    ADMIN = "admin"      # Full access, all commands
    TRADER = "trader"    # Can execute trades, view data
    VIEWER = "viewer"    # Read-only, view only


class Permission(str, Enum):
    """Granular permissions"""
    # Health & monitoring
    VIEW_HEALTH = "view_health"
    VIEW_TIME = "view_time"
    VIEW_LATENCY = "view_latency"
    
    # Market data
    VIEW_PRICE = "view_price"
    VIEW_SPREAD = "view_spread"
    VIEW_KLINES = "view_klines"
    
    # State viewing
    VIEW_STATUS = "view_status"
    VIEW_POSITIONS = "view_positions"
    VIEW_ORDERS = "view_orders"
    VIEW_RECON = "view_recon"
    VIEW_DECISION = "view_decision"
    VIEW_TRACE = "view_trace"
    
    # Control operations
    PAUSE_RESUME = "pause_resume"
    SYNC_NOW = "sync_now"
    CLOSE_POSITION = "close_position"
    CLOSE_ALL = "close_all"


# Permission mapping by role
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.ADMIN: set(Permission),  # All permissions
    UserRole.TRADER: {
        *[p for p in Permission if p.name.startswith("VIEW_")],
        Permission.PAUSE_RESUME,
        Permission.SYNC_NOW,
        Permission.CLOSE_POSITION,
        Permission.CLOSE_ALL,
    },
    UserRole.VIEWER: {
        Permission.VIEW_HEALTH,
        Permission.VIEW_TIME,
        Permission.VIEW_LATENCY,
        Permission.VIEW_PRICE,
        Permission.VIEW_SPREAD,
        Permission.VIEW_KLINES,
        Permission.VIEW_STATUS,
        Permission.VIEW_POSITIONS,
        Permission.VIEW_ORDERS,
        Permission.VIEW_RECON,
        Permission.VIEW_DECISION,
        Permission.VIEW_TRACE,
    },
}


class User:
    """Represents a Telegram user with role and permissions"""

    def __init__(self, chat_id: int, role: UserRole):
        self.chat_id = chat_id
        self.role = role
        self.permissions = ROLE_PERMISSIONS[role]
        self.created_at = datetime.utcnow()
        self.last_command_at: datetime | None = None

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has permission"""
        return permission in self.permissions

    def update_last_command(self) -> None:
        """Update last command timestamp"""
        self.last_command_at = datetime.utcnow()


class RBAC:
    """Role-Based Access Control manager"""

    def __init__(self, admin_ids: list[int], trader_ids: list[int]):
        self.users: Dict[int, User] = {}
        
        # Register admins and traders
        for chat_id in admin_ids:
            self.users[chat_id] = User(chat_id, UserRole.ADMIN)
        
        for chat_id in trader_ids:
            if chat_id not in self.users:
                self.users[chat_id] = User(chat_id, UserRole.TRADER)

    def get_user(self, chat_id: int) -> User | None:
        """Get user by chat ID"""
        return self.users.get(chat_id)

    def is_authorized(self, chat_id: int, permission: Permission) -> bool:
        """Check if user is authorized for permission"""
        user = self.get_user(chat_id)
        if not user:
            return False
        return user.has_permission(permission)

    def is_admin(self, chat_id: int) -> bool:
        """Check if user is admin"""
        user = self.get_user(chat_id)
        if not user:
            return False
        return user.role == UserRole.ADMIN

    def is_registered(self, chat_id: int) -> bool:
        """Check if user is registered"""
        return chat_id in self.users

    def add_user(self, chat_id: int, role: UserRole) -> User:
        """Add or update user"""
        user = User(chat_id, role)
        self.users[chat_id] = user
        return user
