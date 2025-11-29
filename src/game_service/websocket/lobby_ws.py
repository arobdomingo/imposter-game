from __future__ import annotations

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from game_service.websocket.connection_manager import manager
from game_service.repositories import (
    LobbyRepository,
    LobbyMemberRepository,
)


router = APIRouter()


@router.websocket("/ws/lobby/{lobby_id}")
async def websocket_lobby_endpoint(
    websocket: WebSocket,
    lobby_id: int,
    user_id: int = Query(...),
):
    """WebSocket endpoint for lobby real-time updates."""
    # Get database session and repositories
    from shared.database import get_db

    db = next(get_db())
    lobby_repo = LobbyRepository(db)
    lobby_member_repo = LobbyMemberRepository(db)

    try:
        # Verify lobby exists
        lobby = await lobby_repo.get_by_id(lobby_id)
        if not lobby:
            await websocket.close(code=1008, reason="Lobby not found")
            return

        # Verify user is a member of the lobby
        member = await lobby_member_repo.get_member(lobby_id, user_id)
        if not member:
            await websocket.close(code=1008, reason="Not a member of this lobby")
            return
    finally:
        db.close()

    # Connect to lobby
    await manager.connect_lobby(websocket, lobby_id, user_id)

    try:
        # Send initial connection confirmation
        await manager.send_personal_message(
            {
                "type": "connected",
                "lobby_id": lobby_id,
                "user_id": user_id,
                "message": "Connected to lobby",
            },
            websocket,
        )

        # Broadcast that a user connected
        await manager.broadcast_to_lobby(
            {
                "type": "user_connected",
                "lobby_id": lobby_id,
                "user_id": user_id,
            },
            lobby_id,
            exclude=websocket,
        )

        # Keep connection alive and handle messages
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                message_type = message.get("type")

                if message_type == "ping":
                    # Heartbeat
                    await manager.send_personal_message({"type": "pong"}, websocket)
                elif message_type == "lobby_state_request":
                    # Send current lobby state
                    db = next(get_db())
                    lobby_member_repo = LobbyMemberRepository(db)
                    try:
                        members = await lobby_member_repo.list_members(lobby_id)
                        await manager.send_personal_message(
                            {
                                "type": "lobby_state",
                                "lobby_id": lobby_id,
                                "members": [
                                    {
                                        "user_id": m.user_id,
                                        "seat_no": m.seat_no,
                                    }
                                    for m in members
                                ],
                            },
                            websocket,
                        )
                    finally:
                        db.close()

            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {"type": "error", "message": "Invalid JSON"}, websocket
                )
            except Exception as e:
                await manager.send_personal_message(
                    {"type": "error", "message": str(e)}, websocket
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # Broadcast that user disconnected
        await manager.broadcast_to_lobby(
            {
                "type": "user_disconnected",
                "lobby_id": lobby_id,
                "user_id": user_id,
            },
            lobby_id,
        )


async def broadcast_lobby_update(lobby_id: int, update_type: str, data: dict):
    """Helper function to broadcast lobby updates."""
    message = {
        "type": update_type,
        "lobby_id": lobby_id,
        **data,
    }
    await manager.broadcast_to_lobby(message, lobby_id)
