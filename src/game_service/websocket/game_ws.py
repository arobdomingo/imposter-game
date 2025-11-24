from __future__ import annotations

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from game_service.websocket.connection_manager import manager
from game_service.repositories import (
    GameRepository,
    PlayerRepository,
)
from game_service.repositories.chat_message_repo import (
    ChatMessageRepository,
)


router = APIRouter()

# Game statuses that allow chat
CHAT_ALLOWED_STATUSES = {"discussion", "voting"}


@router.websocket("/ws/game/{game_id}")
async def websocket_game_endpoint(
    websocket: WebSocket,
    game_id: int,
    user_id: int = Query(...),
):
    """WebSocket endpoint for game real-time communication."""
    # Get database session and repositories
    from shared.database import get_db

    db = next(get_db())
    game_repo = GameRepository(db)
    player_repo = PlayerRepository(db)
    chat_repo = ChatMessageRepository(db)

    try:
        # Verify game exists
        game = await game_repo.get_by_id(game_id)
        if not game:
            await websocket.close(code=1008, reason="Game not found")
            return

        # Verify user is a player in the game
        player = await player_repo.get_by_user(game_id, user_id)
        if not player:
            await websocket.close(code=1008, reason="Not a player in this game")
            return
    finally:
        db.close()

    # Connect to game
    await manager.connect_game(websocket, game_id, user_id)

    try:
        # Send initial connection confirmation
        await manager.send_personal_message(
            {
                "type": "connected",
                "game_id": game_id,
                "user_id": user_id,
                "game_status": game.status,
                "message": "Connected to game",
            },
            websocket,
        )

        # Send recent chat history if in discussion/voting phase
        if game.status in CHAT_ALLOWED_STATUSES:
            db = next(get_db())
            chat_repo = ChatMessageRepository(db)
            try:
                recent_messages = await chat_repo.list_recent_by_game(game_id, limit=50)
                await manager.send_personal_message(
                    {
                        "type": "chat_history",
                        "messages": [
                            {
                                "id": msg.id,
                                "user_id": msg.user_id,
                                "message": msg.message,
                                "message_type": msg.message_type,
                                "created_at": msg.created_at.isoformat(),
                            }
                            for msg in recent_messages
                        ],
                    },
                    websocket,
                )
            finally:
                db.close()

        # Keep connection alive and handle messages
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                message_type = message.get("type")

                if message_type == "ping":
                    # Heartbeat
                    await manager.send_personal_message({"type": "pong"}, websocket)
                elif message_type == "chat":
                    # Handle chat message
                    db = next(get_db())
                    game_repo = GameRepository(db)
                    player_repo = PlayerRepository(db)
                    chat_repo = ChatMessageRepository(db)
                    try:
                        await handle_chat_message(
                            websocket,
                            game_id,
                            user_id,
                            message,
                            game_repo,
                            player_repo,
                            chat_repo,
                        )
                    finally:
                        db.close()
                elif message_type == "reaction":
                    # Handle reaction
                    db = next(get_db())
                    game_repo = GameRepository(db)
                    player_repo = PlayerRepository(db)
                    chat_repo = ChatMessageRepository(db)
                    try:
                        await handle_reaction(
                            websocket,
                            game_id,
                            user_id,
                            message,
                            game_repo,
                            player_repo,
                            chat_repo,
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


async def handle_chat_message(
    websocket: WebSocket,
    game_id: int,
    user_id: int,
    message_data: dict,
    game_repo: GameRepository,
    player_repo: PlayerRepository,
    chat_repo: ChatMessageRepository,
):
    """Handle incoming chat message."""
    # Verify game is in a chat-allowed status
    game = await game_repo.get_by_id(game_id)
    if not game or game.status not in CHAT_ALLOWED_STATUSES:
        await manager.send_personal_message(
            {
                "type": "error",
                "message": "Chat is only available during discussion and voting phases",
            },
            websocket,
        )
        return

    # Validate message
    text = message_data.get("message", "").strip()
    if not text or len(text) > 500:
        await manager.send_personal_message(
            {
                "type": "error",
                "message": "Message must be between 1 and 500 characters",
            },
            websocket,
        )
        return

    # Store message in database
    chat_message = await chat_repo.create(
        game_id=game_id,
        user_id=user_id,
        message=text,
        message_type="text",
    )

    # Broadcast to all players in the game
    # Note: Imposter messages appear identical to others (no special marking)
    broadcast_message = {
        "type": "chat",
        "game_id": game_id,
        "user_id": user_id,
        "message": text,
        "message_type": "text",
        "created_at": chat_message.created_at.isoformat(),
    }

    await manager.broadcast_to_game(broadcast_message, game_id, exclude=websocket)


async def handle_reaction(
    websocket: WebSocket,
    game_id: int,
    user_id: int,
    message_data: dict,
    game_repo: GameRepository,
    player_repo: PlayerRepository,
    chat_repo: ChatMessageRepository,
):
    """Handle incoming reaction."""
    # Verify game is in a chat-allowed status
    game = await game_repo.get_by_id(game_id)
    if not game or game.status not in CHAT_ALLOWED_STATUSES:
        await manager.send_personal_message(
            {
                "type": "error",
                "message": "Reactions are only available during discussion and voting phases",
            },
            websocket,
        )
        return

    # Validate reaction
    reaction = message_data.get("reaction", "").strip()
    if not reaction or len(reaction) > 50:
        await manager.send_personal_message(
            {
                "type": "error",
                "message": "Reaction must be between 1 and 50 characters",
            },
            websocket,
        )
        return

    # Store reaction in database
    chat_message = await chat_repo.create(
        game_id=game_id,
        user_id=user_id,
        message=reaction,
        message_type="reaction",
    )

    # Broadcast to all players
    broadcast_message = {
        "type": "reaction",
        "game_id": game_id,
        "user_id": user_id,
        "reaction": reaction,
        "created_at": chat_message.created_at.isoformat(),
    }

    await manager.broadcast_to_game(broadcast_message, game_id, exclude=websocket)
