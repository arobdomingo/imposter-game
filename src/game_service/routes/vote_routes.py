'''from fastapi import APIRouter, Depends, HTTPException

from game_service.schemas.vote import (
    VoteRequestSchema,
    VoteResultSchema,
    ScoreResultSchema,
)
from game_service.repositories.vote_repo import get_vote_repository, VoteRepository
from game_service.repositories.player_repo import (
    get_player_repository,
    PlayerRepository,
)
from game_service.repositories.game_repo import get_game_repository, GameRepository
from game_service.services.scoring_service import get_scoring_service, ScoringService

router = APIRouter(prefix="/games", tags=["voting"])


@router.post("/{game_id}/votes", response_model=VoteResultSchema)
async def submit_vote(
    game_id: int,
    payload: VoteRequestSchema,
    vote_repo: VoteRepository = Depends(get_vote_repository),
    player_repo: PlayerRepository = Depends(get_player_repository),
    game_repo: GameRepository = Depends(get_game_repository),
):
    # validate game
    game = await game_repo.get_by_id(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.status != "voting":
        raise HTTPException(status_code=400, detail="Game not in voting phase")

    # validate voter
    voter = await player_repo.get_by_id(payload.voter_id)
    if not voter or voter.game_id != game_id:
        raise HTTPException(status_code=403, detail="Voter not in this game")

    # prevent self vote
    if payload.target_id is not None and payload.target_id == payload.voter_id:
        raise HTTPException(status_code=400, detail="Cannot vote for yourself")

    # check existing vote
    existing = await vote_repo.get_by_voter(game_id, payload.voter_id)
    if existing:
        raise HTTPException(
            status_code=409, detail="Voter has already voted this round"
        )

    vote = await vote_repo.create(
        game_id=game_id, voter_id=payload.voter_id, target_id=payload.target_id
    )
    return vote


@router.post("/{game_id}/votes/score", response_model=ScoreResultSchema)
async def finalize_votes(
    game_id: int,
    scoring_service: ScoringService = Depends(get_scoring_service),
    vote_repo: VoteRepository = Depends(get_vote_repository),
    player_repo: PlayerRepository = Depends(get_player_repository),
    game_repo: GameRepository = Depends(get_game_repository),
):
    game = await game_repo.get_by_id(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    result = scoring_service.compute_and_apply_scores(game_id)

    await game_repo.update_status(
        game_id, "round_finished", current_round=game.current_round
    )
    await vote_repo.clear_game_votes(game_id)

    return ScoreResultSchema(
        game_id=game_id,
        impostor_ids=result["impostor_ids"],
        player_scores=result["player_scores"],
    )'''



# src/game_service/routes/vote_routes.py

from fastapi import APIRouter, Depends, HTTPException
from shared.database import get_db
from sqlalchemy.orm import Session

from game_service.repositories.vote_repo import VoteRepository
from game_service.repositories.game_repo import GameRepository
from game_service.repositories.player_repo import PlayerRepository
from game_service.services.scoring_service import ScoringService
from game_service.schemas.vote import VoteRequestSchema, VoteResultSchema, ScoreResultSchema

router = APIRouter(prefix="/games/{game_id}/votes", tags=["votes"])


@router.post("", response_model=VoteResultSchema)
async def submit_vote(
    game_id: int,
    vote: VoteRequestSchema,
    db: Session = Depends(get_db)
):
    """
    Accept vote submission:
    - voter_id votes for target_id
    """

    game_repo = GameRepository(db)
    player_repo = PlayerRepository(db)
    vote_repo = VoteRepository(db)

    # Validate game
    game = await game_repo.get_by_id(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Validate both players belong to the game
    voter = await player_repo.get_player_by_id(vote.voter_id)
    target = await player_repo.get_player_by_id(vote.target_id)

    if not voter or voter.game_id != game_id:
        raise HTTPException(status_code=400, detail="Invalid voter")

    if not target or target.game_id != game_id:
        raise HTTPException(status_code=400, detail="Invalid target")

    # Create vote
    new_vote = await vote_repo.create(
    game_id=game_id,
    voter_id=vote.voter_id,
    target_id=vote.target_id,
)


    return VoteResultSchema(
    id=new_vote.id,
    game_id=new_vote.game_id,
    voter_id=new_vote.voter_id,
    target_id=new_vote.target_id,
    created_at=new_vote.created_at,
)



@router.post("/score", response_model=ScoreResultSchema)
async def compute_scores(
    game_id: int,
    db: Session = Depends(get_db)
):
    """
    Compute the final scores after voting.
    """

    score_service = ScoringService(db)
    result = await score_service.compute_scores(game_id)
    return result


