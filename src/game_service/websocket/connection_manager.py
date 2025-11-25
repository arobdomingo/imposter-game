from __future__ import annotations

from typing import Dict, Set
from fastapi import WebSocket
from collections import defaultdict


class ConnectionManager:
    """Manages WebSocket connections for lobbies and games."""

    def __init__(self):
        # Map lobby_id -> Set of WebSocket connections
        self.lobby_connections: Dict[int, Set[WebSocket]] = defaultdict(set)
        # Map game_id -> Set of WebSocket connections
        self.game_connections: Dict[int, Set[WebSocket]] = defaultdict(set)
        # Map WebSocket -> (lobby_id, game_id, user_id)
        self.connection_info: Dict[WebSocket, tuple[int | None, int | None, int]] = {}

    async def connect_lobby(self, websocket: WebSocket, lobby_id: int, user_id: int):
        """Connect a WebSocket to a lobby."""
        await websocket.accept()
        self.lobby_connections[lobby_id].add(websocket)
        self.connection_info[websocket] = (lobby_id, None, user_id)

    async def connect_game(self, websocket: WebSocket, game_id: int, user_id: int):
        """Connect a WebSocket to a game."""
        await websocket.accept()
        self.game_connections[game_id].add(websocket)
        self.connection_info[websocket] = (None, game_id, user_id)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        info = self.connection_info.get(websocket)
        if info:
            lobby_id, game_id, _ = info
            if lobby_id:
                self.lobby_connections[lobby_id].discard(websocket)
            if game_id:
                self.game_connections[game_id].discard(websocket)
            del self.connection_info[websocket]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket."""
        try:
            await websocket.send_json(message)
        except Exception:
            # Connection might be closed
            self.disconnect(websocket)

    async def broadcast_to_lobby(
        self, message: dict, lobby_id: int, exclude: WebSocket | None = None
    ):
        """Broadcast a message to all connections in a lobby."""
        disconnected = []
        for connection in self.lobby_connections[lobby_id]:
            if connection != exclude:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)

        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_to_game(
        self, message: dict, game_id: int, exclude: WebSocket | None = None
    ):
        """Broadcast a message to all connections in a game."""
        disconnected = []
        for connection in self.game_connections[game_id]:
            if connection != exclude:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)

        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

    def get_lobby_connections_count(self, lobby_id: int) -> int:
        """Get the number of active connections for a lobby."""
        return len(self.lobby_connections[lobby_id])

    def get_game_connections_count(self, game_id: int) -> int:
        """Get the number of active connections for a game."""
        return len(self.game_connections[game_id])


# Global connection manager instance
manager = ConnectionManager()
