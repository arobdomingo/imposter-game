from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from shared.database import get_db
from game_service.repositories import (
    LobbyRepository,
    LobbyMemberRepository,
    PlayerRepository,
    get_lobby_repository,
    get_lobby_member_repository,
    get_player_repository,
)
from game_service.repositories import (
    GameRepository,
    get_game_repository,
)
from game_service.services.lobby_service import LobbyService
from game_service.services.game_engine import GameEngine, get_game_engine
from game_service.schemas.lobby import (
    LobbyCreateSchema,
    LobbyJoinSchema,
    LobbyLeaveSchema,
    LobbyResponseSchema,
    LobbyStateSchema,
    LobbyPlayerSchema,
)
from user_service.models.user import UserRepository, get_user_repository


router = APIRouter(prefix="/v2/lobbies", tags=["Lobbies"])


def get_lobby_service(
    db: Session = Depends(get_db),
    lobby_repo: LobbyRepository = Depends(get_lobby_repository),
    lobby_member_repo: LobbyMemberRepository = Depends(get_lobby_member_repository),
    game_repo: GameRepository = Depends(get_game_repository),
    game_engine: GameEngine = Depends(get_game_engine),
) -> LobbyService:
    return LobbyService(lobby_repo, lobby_member_repo, game_repo, game_engine)


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_lobby(
    data: LobbyCreateSchema,
    lobby_service: LobbyService = Depends(get_lobby_service),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Create a new lobby."""
    # Verify user exists
    user = await user_repo.get_by_id(data.host_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    lobby_id, code = await lobby_service.create_lobby(data.host_id)
    return {"lobby_id": lobby_id, "code": code}


@router.post("/{lobby_id}/join", status_code=status.HTTP_200_OK)
async def join_lobby(
    lobby_id: int,
    data: LobbyJoinSchema,
    lobby_repo: LobbyRepository = Depends(get_lobby_repository),
    lobby_service: LobbyService = Depends(get_lobby_service),
    lobby_member_repo: LobbyMemberRepository = Depends(get_lobby_member_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Join an existing lobby by lobby ID."""
    # Verify user exists
    user = await user_repo.get_by_id(data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    success = await lobby_service.join_lobby(lobby_id, data.user_id)
    if not success:
        # Get more specific error message
        lobby = await lobby_repo.get_by_id(lobby_id)
        if not lobby:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lobby not found",
            )
        if lobby.status != "waiting":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot join lobby (lobby is already playing or finished)",
            )
        # Check if lobby is full
        count = await lobby_member_repo.count_members(lobby_id)
        if count >= 4:  # MAX_PLAYERS
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot join lobby (lobby is full)",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot join lobby (unknown error)",
        )

    return {"message": "Successfully joined lobby"}


@router.post("/code/{code}/join", status_code=status.HTTP_200_OK)
async def join_lobby_by_code(
    code: str,
    data: LobbyJoinSchema,
    lobby_repo: LobbyRepository = Depends(get_lobby_repository),
    lobby_service: LobbyService = Depends(get_lobby_service),
    lobby_member_repo: LobbyMemberRepository = Depends(get_lobby_member_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Join an existing lobby by lobby code."""
    # Find lobby by code
    lobby = await lobby_repo.get_by_code(code)
    if not lobby:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lobby not found",
        )

    # Verify user exists
    user = await user_repo.get_by_id(data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    success = await lobby_service.join_lobby(lobby.id, data.user_id)
    if not success:
        # Get more specific error message
        if lobby.status != "waiting":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot join lobby (lobby is already playing or finished)",
            )
        # Check if lobby is full
        count = await lobby_member_repo.count_members(lobby.id)
        if count >= 4:  # MAX_PLAYERS
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot join lobby (lobby is full)",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot join lobby (unknown error)",
        )

    return {"message": "Successfully joined lobby", "lobby_id": lobby.id}


@router.post("/{lobby_id}/leave", status_code=status.HTTP_200_OK)
async def leave_lobby(
    lobby_id: int,
    data: LobbyLeaveSchema,
    lobby_service: LobbyService = Depends(get_lobby_service),
):
    """Leave a lobby."""
    success = await lobby_service.leave_lobby(lobby_id, data.user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot leave lobby (not a member or game in progress)",
        )

    return {"message": "Successfully left lobby"}


@router.get("/{lobby_id}", response_model=LobbyStateSchema)
async def get_lobby_state(
    lobby_id: int,
    lobby_repo: LobbyRepository = Depends(get_lobby_repository),
    lobby_member_repo: LobbyMemberRepository = Depends(get_lobby_member_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    game_repo: GameRepository = Depends(get_game_repository),
):
    """Get the current state of a lobby."""
    lobby = await lobby_repo.get_by_id(lobby_id)
    if not lobby:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lobby not found",
        )

    members = await lobby_member_repo.list_members(lobby_id)
    player_schemas = []
    for member in members:
        # Try to get user name, but don't fail if user doesn't exist
        user_name = None
        try:
            user = await user_repo.get_by_id(member.user_id)
            if user:
                user_name = user.name
        except Exception:
            # User not found or other error - continue without name
            pass

        player_schemas.append(
            LobbyPlayerSchema(
                user_id=member.user_id,
                seat_no=member.seat_no or 0,
                user_name=user_name,
            )
        )

    # If lobby is playing, get the active game ID
    active_game_id = None
    if lobby.status == "playing":
        active_game = await game_repo.get_active_by_lobby(lobby.id)
        if active_game:
            active_game_id = active_game.id

    return LobbyStateSchema(
        lobby=LobbyResponseSchema(
            id=lobby.id,
            code=lobby.code,
            host_id=lobby.host_id,
            status=lobby.status,
            created_at=lobby.created_at,
        ),
        players=player_schemas,
        active_game_id=active_game_id,
    )


@router.get("/code/{code}", response_model=LobbyStateSchema)
async def get_lobby_by_code(
    code: str,
    lobby_repo: LobbyRepository = Depends(get_lobby_repository),
    lobby_member_repo: LobbyMemberRepository = Depends(get_lobby_member_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    game_repo: GameRepository = Depends(get_game_repository),
):
    """Get lobby state by lobby code."""
    lobby = await lobby_repo.get_by_code(code)
    if not lobby:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lobby not found",
        )

    members = await lobby_member_repo.list_members(lobby.id)
    player_schemas = []
    for member in members:
        # Try to get user name, but don't fail if user doesn't exist
        user_name = None
        try:
            user = await user_repo.get_by_id(member.user_id)
            if user:
                user_name = user.name
        except Exception:
            # User not found or other error - continue without name
            pass

        player_schemas.append(
            LobbyPlayerSchema(
                user_id=member.user_id,
                seat_no=member.seat_no or 0,
                user_name=user_name,
            )
        )

    # If lobby is playing, get the active game ID
    active_game_id = None
    if lobby.status == "playing":
        active_game = await game_repo.get_active_by_lobby(lobby.id)
        if active_game:
            active_game_id = active_game.id

    return LobbyStateSchema(
        lobby=LobbyResponseSchema(
            id=lobby.id,
            code=lobby.code,
            host_id=lobby.host_id,
            status=lobby.status,
            created_at=lobby.created_at,
        ),
        players=player_schemas,
        active_game_id=active_game_id,
    )


@router.post("/{lobby_id}/start", status_code=200)
async def start_game(
    lobby_id: int,
    request: dict,
    lobby_repo: LobbyRepository = Depends(get_lobby_repository),
    lobby_member_repo: LobbyMemberRepository = Depends(get_lobby_member_repository),
    game_repo: GameRepository = Depends(get_game_repository),
    game_engine: GameEngine = Depends(get_game_engine),
):
    """
    Start the game from a lobby.
    Expected JSON body of Request:
    {"host_id": <int>, "mode": "standard"}
    """

    host_id = request.get("host_id")
    mode = request.get("mode", "standard")

    # Validate lobby
    lobby = await lobby_repo.get_by_id(lobby_id)
    if not lobby:
        raise HTTPException(404, "Lobby not found")

    # Validate that host_id matches lobby.host_id
    if lobby.host_id != host_id:
        raise HTTPException(403, "Only the host can start the game")

    # If lobby is playing, ensure the game is finished before starting a new one
    if lobby.status == "playing":
        active_game = await game_repo.get_active_by_lobby(lobby_id)
        if active_game and active_game.status != "finished":
            raise HTTPException(
                400,
                "Current game is not finished yet. Please wait for the game to end.",
            )
        # Update lobby status to waiting if game is finished
        await lobby_repo.update_status(lobby_id, "waiting")

    # Get lobby members
    members = await lobby_member_repo.list_members(lobby_id)
    user_ids = [m.user_id for m in members]

    if len(user_ids) < 3:
        raise HTTPException(400, "At least 3 players required to start a game")

    # Start the game
    game_id = await game_engine.start_game(
        lobby_id=lobby_id,
        player_user_ids=user_ids,
        mode=mode,
    )

    return {"game_id": game_id}


# to be added to seperate files for organization purposes
# future names provided above current names (e.g. current: "/{lobby_id}/game", incoming change to: "v2/games/{game_id}")


# @router.get("v2/games/{game_id}", status_code=200)
@router.get("/{lobby_id}/game", status_code=200)
async def get_game_state(
    lobby_id: int,
    lobby_repo: LobbyRepository = Depends(get_lobby_repository),
    game_repo: GameRepository = Depends(get_game_repository),
    player_repo: PlayerRepository = Depends(get_player_repository),
):
    """Return the current game's state for the lobby (no spoilers)."""

    lobby = await lobby_repo.get_by_id(lobby_id)
    if not lobby:
        raise HTTPException(404, "Lobby not found")

    # Get the most recent game (including finished ones)
    # First try active game, then try to get the latest game
    game = await game_repo.get_active_by_lobby(lobby_id)
    if not game:
        # If no active game, try to get the latest game (including finished)
        from sqlalchemy import select, desc
        from game_service.models.game import Game

        stmt = (
            select(Game)
            .where(Game.lobby_id == lobby_id)
            .order_by(desc(Game.id))
            .limit(1)
        )
        game = game_repo.session.scalar(stmt)
        if not game:
            raise HTTPException(404, "No game started yet")

    players = await player_repo.list_by_game(game.id)

    return {
        "game_id": game.id,
        "mode": game.mode,
        "status": game.status,  # Include game status
        "players": [
            {
                "id": p.id,  # Include player_id for voting
                "user_id": p.user_id,
                "seat_no": p.seat_no,
                # Do NOT expose impostor identity
            }
            for p in players
        ],
    }


# @router.get("/v2/games/{game_id}/role", status_code=200)
@router.get("/{game_id}/role")
async def get_my_role(
    game_id: int,
    user_id: int,
    player_repo: PlayerRepository = Depends(get_player_repository),
):
    """Return the current player's word and role for this game."""

    player = await player_repo.get_by_user(game_id, user_id)
    if not player:
        raise HTTPException(404, "Player not found in this game")

    return {
        "user_id": user_id,
        "player_id": player.id,  # Include player_id for clue submission
        "is_imposter": player.is_imposter,
        "word": player.word,
        "seat_no": player.seat_no,
    }


# @router.get("/v2/games/{game_id}/end", status_code=200)
@router.post("/{lobby_id}/game/end", status_code=200)
async def end_game(
    lobby_id: int,
    request: dict,
    lobby_repo: LobbyRepository = Depends(get_lobby_repository),
    game_repo: GameRepository = Depends(get_game_repository),
):
    """
    End the current active game for this lobby.
    Expected JSON body:
    {
      "host_id": <int>
    }
    """

    host_id = request.get("host_id")

    # 1) Validate lobby exists
    lobby = await lobby_repo.get_by_id(lobby_id)
    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")

    # 2) Check that caller is the host
    if lobby.host_id != host_id:
        raise HTTPException(status_code=403, detail="Only the host can end the game")

    # 3) Find active game for this lobby
    game = await game_repo.get_active_by_lobby(lobby_id)
    if not game:
        raise HTTPException(status_code=404, detail="No active game for this lobby")

    await game_repo.update_status(game.id, status="finished")
    await lobby_repo.update_status(lobby_id, status="waiting")

    return {"message": "Game finished", "game_id": game.id}
