from fastapi import APIRouter, Depends, HTTPException
from game_service.schemas.clue import ClueSubmitSchema
from game_service.repositories.clue_repo import get_clue_repository, ClueRepository
from game_service.repositories.player_repo import (
    get_player_repository,
    PlayerRepository,
)
from game_service.repositories.game_repo import get_game_repository, GameRepository

router = APIRouter(prefix="/games", tags=["clues"])


@router.get("/{game_id}/clues/{round_number}")
async def get_clues_for_round(
    game_id: int,
    round_number: int,
    clue_repo: ClueRepository = Depends(get_clue_repository),
    player_repo: PlayerRepository = Depends(get_player_repository),
):
    """Get all submitted clues for a specific round."""
    clues = await clue_repo.list_by_round(game_id, round_number)
    players = await player_repo.list_by_game(game_id)
    player_map = {p.id: p for p in players}

    result = []
    for clue in clues:
        player = player_map.get(clue.player_id)
        if player:
            result.append(
                {
                    "player_id": player.id,
                    "user_id": player.user_id,
                    "seat_no": player.seat_no,
                    "clue_word": clue.clue_word,
                    "submitted_at": clue.submitted_at.isoformat()
                    if clue.submitted_at
                    else None,
                }
            )

    return {"clues": result}


@router.post("/{game_id}/clues/submit")
async def submit_clue(
    game_id: int,
    payload: ClueSubmitSchema,
    clue_repo: ClueRepository = Depends(get_clue_repository),
    player_repo: PlayerRepository = Depends(get_player_repository),
    game_repo: GameRepository = Depends(get_game_repository),
):
    game = await game_repo.get_by_id(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    player = await player_repo.get_by_id(payload.player_id)
    if not player or player.game_id != game_id:
        raise HTTPException(status_code=403, detail="Player not in this game")

    # Check if player already submitted for this round
    existing = await clue_repo.get_by_player_round(
        game_id, payload.player_id, payload.round_number
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="Clue already submitted for this round"
        )

    # No order validation - players can submit simultaneously

    # Handle skipped clues
    # For skipped clues, use a placeholder word instead of empty string
    # to satisfy database NOT NULL constraint
    clue_word = payload.clue_word.strip() if payload.clue_word else ""
    if payload.skipped:
        clue_word = "(skipped)"  # Use placeholder for skipped clues
    elif not clue_word:
        # If no clue word provided and not explicitly skipped, treat as skipped
        clue_word = "(skipped)"

    clue = await clue_repo.create(
        game_id=game_id,
        player_id=payload.player_id,
        round_number=payload.round_number,
        clue_word=clue_word,
        skipped=payload.skipped,
    )

    # Get all submitted clues for this round (for Imposter to see)
    previous = []
    players = await player_repo.list_by_game(game_id)
    clues_all = await clue_repo.list_by_round(game_id, payload.round_number)

    # Create a map of player_id to player info
    player_map = {p.id: p for p in players}

    # Add all submitted clues (except current player's own clue)
    for c in clues_all:
        if c.player_id != payload.player_id:
            p = player_map.get(c.player_id)
            if p:
                previous.append(
                    {
                        "player_id": p.id,
                        "user_id": p.user_id,
                        "clue_word": c.clue_word,
                        "seat_no": p.seat_no,
                    }
                )

    clues_all = await clue_repo.list_by_round(game_id, payload.round_number)
    all_submitted = len({c.player_id for c in clues_all}) >= len(players)

    if all_submitted:
        await game_repo.update_status(
            game_id, "voting", current_round=game.current_round
        )

    # Return response with all required fields
    return {
        "id": clue.id,
        "player_id": clue.player_id,
        "round_number": clue.round_number,
        "clue_word": clue.clue_word,
        "skipped": clue.skipped,
        "submitted_at": clue.submitted_at.isoformat() if clue.submitted_at else None,
        "previous_clues": previous,
        "can_submit_next": all_submitted is False,
        "move_to_voting": all_submitted,
    }
