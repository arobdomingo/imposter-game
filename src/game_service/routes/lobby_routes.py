from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from shared.database import get_db
from game_service.repositories import (
    LobbyRepository,
    LobbyMemberRepository,
    get_lobby_repository,
    get_lobby_member_repository,
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
    lobby_service: LobbyService = Depends(get_lobby_service),
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot join lobby (lobby full, already playing, or not found)",
        )

    return {"message": "Successfully joined lobby"}


@router.post("/code/{code}/join", status_code=status.HTTP_200_OK)
async def join_lobby_by_code(
    code: str,
    data: LobbyJoinSchema,
    lobby_repo: LobbyRepository = Depends(get_lobby_repository),
    lobby_service: LobbyService = Depends(get_lobby_service),
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot join lobby (lobby full or already playing)",
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
        player_schemas.append(
            LobbyPlayerSchema(
                user_id=member.user_id,
                seat_no=member.seat_no or 0,
            )
        )

    return LobbyStateSchema(
        lobby=LobbyResponseSchema(
            id=lobby.id,
            code=lobby.code,
            host_id=lobby.host_id,
            status=lobby.status,
            created_at=lobby.created_at,
        ),
        players=player_schemas,
    )


@router.get("/code/{code}", response_model=LobbyStateSchema)
async def get_lobby_by_code(
    code: str,
    lobby_repo: LobbyRepository = Depends(get_lobby_repository),
    lobby_member_repo: LobbyMemberRepository = Depends(get_lobby_member_repository),
    user_repo: UserRepository = Depends(get_user_repository),
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
        player_schemas.append(
            LobbyPlayerSchema(
                user_id=member.user_id,
                seat_no=member.seat_no or 0,
            )
        )

    return LobbyStateSchema(
        lobby=LobbyResponseSchema(
            id=lobby.id,
            code=lobby.code,
            host_id=lobby.host_id,
            status=lobby.status,
            created_at=lobby.created_at,
        ),
        players=player_schemas,
    )
