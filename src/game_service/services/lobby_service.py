from __future__ import annotations

import random
import string
from typing import Optional

from game_service.repositories import (
    LobbyRepository,
    LobbyMemberRepository,
    GameRepository,
)
from game_service.services.game_engine import GameEngine
from game_service.websocket.connection_manager import manager


class LobbyService:
    """Service for managing lobby operations."""

    CODE_LENGTH = 6
    MAX_PLAYERS = 4

    def __init__(
        self,
        lobby_repo: LobbyRepository,
        lobby_member_repo: LobbyMemberRepository,
        game_repo: GameRepository,
        game_engine: GameEngine,
    ):
        self.lobby_repo = lobby_repo
        self.lobby_member_repo = lobby_member_repo
        self.game_repo = game_repo
        self.game_engine = game_engine

    async def generate_unique_code(self) -> str:
        """Generate a unique lobby code."""
        max_attempts = 100
        for _ in range(max_attempts):
            code = "".join(
                random.choices(
                    string.ascii_uppercase + string.digits, k=self.CODE_LENGTH
                )
            )
            existing = await self.lobby_repo.get_by_code(code)
            if existing is None:
                return code
        raise RuntimeError("Failed to generate unique lobby code")

    async def create_lobby(self, host_id: int) -> tuple[int, str]:
        """Create a new lobby and add the host as the first member."""
        code = await self.generate_unique_code()
        lobby = await self.lobby_repo.create(code=code, host_id=host_id)
        # Add host as first member
        await self.lobby_member_repo.add_member(lobby.id, host_id, seat_no=1)
        return lobby.id, code

    async def join_lobby(self, lobby_id: int, user_id: int) -> bool:
        """
        Add a user to a lobby.
        Returns True if successful, False if lobby is full or already playing.
        """
        lobby = await self.lobby_repo.get_by_id(lobby_id)
        if not lobby:
            return False

        if lobby.status != "waiting":
            return False  # Lobby is already playing or finished

        # Check if user is already in lobby
        existing = await self.lobby_member_repo.get_member(lobby_id, user_id)
        if existing:
            return True  # Already a member

        # Check if lobby is full
        count = await self.lobby_member_repo.count_members(lobby_id)
        if count >= self.MAX_PLAYERS:
            return False

        # Assign seat number
        seat_no = count + 1
        await self.lobby_member_repo.add_member(lobby_id, user_id, seat_no=seat_no)

        # Broadcast player joined event
        await manager.broadcast_to_lobby(
            {
                "type": "player_joined",
                "lobby_id": lobby_id,
                "user_id": user_id,
                "seat_no": seat_no,
            },
            lobby_id,
        )

        # Check if we should auto-start the game
        new_count = await self.lobby_member_repo.count_members(lobby_id)
        if new_count == self.MAX_PLAYERS:
            await self._auto_start_game(lobby_id)

        return True

    async def leave_lobby(self, lobby_id: int, user_id: int) -> bool:
        """Remove a user from a lobby."""
        lobby = await self.lobby_repo.get_by_id(lobby_id)
        if not lobby:
            return False

        if lobby.status != "waiting":
            return False  # Can't leave during a game

        removed = await self.lobby_member_repo.remove_member(lobby_id, user_id)
        if not removed:
            return False

        # Broadcast player left event
        await manager.broadcast_to_lobby(
            {
                "type": "player_left",
                "lobby_id": lobby_id,
                "user_id": user_id,
            },
            lobby_id,
        )

        # If host left, we might want to transfer host or close lobby
        # For now, we'll just remove the member
        return True

    async def _auto_start_game(self, lobby_id: int) -> Optional[int]:
        """Automatically start a game when lobby is full."""
        lobby = await self.lobby_repo.get_by_id(lobby_id)
        if not lobby or lobby.status != "waiting":
            return None

        members = await self.lobby_member_repo.list_members(lobby_id)
        if len(members) != self.MAX_PLAYERS:
            return None

        # Get user IDs in seat order
        user_ids = [
            member.user_id for member in sorted(members, key=lambda m: m.seat_no or 0)
        ]

        # Start the game (mode can be configurable, defaulting to "aware")
        game_id = await self.game_engine.start_game(lobby_id, user_ids, mode="aware")
        return game_id
