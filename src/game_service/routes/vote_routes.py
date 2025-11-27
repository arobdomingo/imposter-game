from fastapi import APIRouter, Depends, HTTPException
from shared.database import get_db
from sqlalchemy.orm import Session

from game_service.repositories.vote_repo import VoteRepository
from game_service.repositories.game_repo import GameRepository
from game_service.repositories.player_repo import PlayerRepository
from game_service.services.scoring_service import ScoringService
from game_service.schemas.vote import (
    VoteRequestSchema,
    VoteResultSchema,
    ScoreResultSchema,
)

router = APIRouter(prefix="/games/{game_id}/votes", tags=["votes"])


@router.post("", response_model=VoteResultSchema)
async def submit_vote(
    game_id: int, vote: VoteRequestSchema, db: Session = Depends(get_db)
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

    voter = await player_repo.get_player_by_id(vote.voter_id)
    target = await player_repo.get_player_by_id(vote.target_id)

    if not voter or voter.game_id != game_id:
        raise HTTPException(status_code=400, detail="Invalid voter")

    if not target or target.game_id != game_id:
        raise HTTPException(status_code=400, detail="Invalid target")

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
async def compute_scores(game_id: int, db: Session = Depends(get_db)):
    """
    Compute the final scores after voting.
    """

    score_service = ScoringService(db)
    result = await score_service.compute_scores(game_id)
    return result
