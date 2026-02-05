"""
WebSocket connection manager with user-based rate limiting.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from fastapi import WebSocket


@dataclass
class UserConnection:
    """Represents a single WebSocket connection."""

    websocket: WebSocket
    user_id: str
    session_id: Optional[str] = None
    connected_at: datetime = field(default_factory=datetime.now)


class WebSocketManager:
    """
    Manages WebSocket connections with user-based limits.

    Features:
    - Track active connections per user
    - Limit max concurrent connections per user
    - Clean up stale connections
    """

    def __init__(self, max_connections_per_user: int = 3):
        self.max_connections_per_user = max_connections_per_user
        # user_id -> list of UserConnection
        self._connections: dict[str, list[UserConnection]] = defaultdict(list)

    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of active connections for a user."""
        return len(self._connections.get(user_id, []))

    def can_connect(self, user_id: str) -> bool:
        """Check if user can create a new connection."""
        return self.get_user_connection_count(user_id) < self.max_connections_per_user

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> Optional[UserConnection]:
        """
        Register a new WebSocket connection.

        Returns UserConnection if successful, None if limit exceeded.
        """
        if not self.can_connect(user_id):
            return None

        await websocket.accept()

        connection = UserConnection(
            websocket=websocket,
            user_id=user_id,
            session_id=session_id,
        )

        self._connections[user_id].append(connection)
        return connection

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a WebSocket connection."""
        if user_id in self._connections:
            self._connections[user_id] = [
                conn
                for conn in self._connections[user_id]
                if conn.websocket != websocket
            ]
            # Clean up empty lists
            if not self._connections[user_id]:
                del self._connections[user_id]

    def get_user_connections(self, user_id: str) -> list[UserConnection]:
        """Get all connections for a user."""
        return self._connections.get(user_id, [])

    async def broadcast_to_user(self, user_id: str, message: dict):
        """Send message to all connections of a user."""
        for conn in self._connections.get(user_id, []):
            try:
                await conn.websocket.send_json(message)
            except Exception:
                # Connection might be closed
                pass

    async def close_user_connections(self, user_id: str, reason: str = ""):
        """Close all connections for a user."""
        for conn in self._connections.get(user_id, []):
            try:
                await conn.websocket.close(code=1000, reason=reason)
            except Exception:
                pass
        if user_id in self._connections:
            del self._connections[user_id]

    @property
    def total_connections(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self._connections.values())

    @property
    def connected_users(self) -> int:
        """Get number of users with active connections."""
        return len(self._connections)

    def get_stats(self) -> dict:
        """Get connection statistics."""
        return {
            "total_connections": self.total_connections,
            "connected_users": self.connected_users,
            "max_per_user": self.max_connections_per_user,
            "users": {
                user_id: len(conns) for user_id, conns in self._connections.items()
            },
        }


# Global instance
ws_manager = WebSocketManager(max_connections_per_user=3)
