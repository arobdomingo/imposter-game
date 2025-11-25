from fastapi import APIRouter, Depends, HTTPException

from game_service.schemas.clue import ClueSubmitSchema, ClueResponseSchema
from game_service.repositories.clue_repo import get_clue_repository, ClueRepository
from game_service.repositories.player_repo import (
    get_player_repository,
    PlayerRepository,
)
from game_service.repositories.game_repo import get_game_repository, GameRepository

router = APIRouter(prefix="/games", tags=["clues"])


@router.post("/{game_id}/clues/submit", response_model=ClueResponseSchema)
async def submit_clue(
    game_id: int,
    payload: ClueSubmitSchema,
    clue_repo: ClueRepository = Depends(get_clue_repository),
    player_repo: PlayerRepository = Depends(get_player_repository),
    game_repo: GameRepository = Depends(get_game_repository),
):

    # validate game
    game = await game_repo.get_by_id(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # validate player exists and belongs to game
    player = await player_repo.get_by_id(payload.player_id)
    if not player or player.game_id != game_id:
        raise HTTPException(status_code=403, detail="Player not in this game")

    # sequential enforcement: check seat_no of player and ensure all previous seats have clues
    seat = player.seat_no
    if seat > 1:
        # check previous seats 1..seat-1
        for prev_seat in range(1, seat):
            prev_player = await player_repo.get_by_seat(game_id, prev_seat)
            if not prev_player:
                raise HTTPException(
                    status_code=400, detail=f"Previous seat {prev_seat} missing"
                )
            existing = await clue_repo.get_by_player_round(
                game_id, prev_player.id, payload.round_number
            )
            if not existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot submit: player in seat {prev_seat} has not submitted yet",
                )

    # check for duplicate submission by same player for this round
    existing = await clue_repo.get_by_player_round(
        game_id, payload.player_id, payload.round_number
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="Clue already submitted for this round"
        )

    # persist clue
    clue = await clue_repo.create(
        game_id=game_id,
        player_id=payload.player_id,
        round_number=payload.round_number,
        clue_word=payload.clue_word.strip(),
        skipped=payload.skipped,
    )

    # build previous_clues visible to caller (all players with seat < player's seat)
    previous = []
    players = await player_repo.list_by_game(game_id)
    # map seat -> player
    seat_map = {p.seat_no: p for p in players}
    for s in range(1, player.seat_no):
        p = seat_map.get(s)
        if not p:
            continue
        c = await clue_repo.get_by_player_round(game_id, p.id, payload.round_number)
        if c:
            previous.append({"player_id": p.id, "clue_word": c.clue_word})

    # determine if all players submitted -> move to voting
    clues_all = await clue_repo.list_by_round(game_id, payload.round_number)
    all_submitted = len({c.player_id for c in clues_all}) >= len(players)

    response = {
        "id": clue.id,
        "player_id": clue.player_id,
        "round_number": clue.round_number,
        "clue_word": clue.clue_word,
        "skipped": clue.skipped,
        "previous_clues": previous,
        "can_submit_next": all_submitted is False,
        "move_to_voting": all_submitted,
    }

    # If all submitted, flip game status to "voting"
    if all_submitted:
        await game_repo.update_status(
            game_id, "voting", current_round=game.current_round
        )

    return response
