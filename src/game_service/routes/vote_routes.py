from fastapi import APIRouter, Depends, HTTPException
from shared.database import get_db
from sqlalchemy.orm import Session

from game_service.repositories.vote_repo import VoteRepository
from game_service.repositories.game_repo import GameRepository, get_game_repository
from game_service.repositories.player_repo import PlayerRepository
from game_service.services.scoring_service import ScoringService
from game_service.schemas.vote import (
    VoteRequestSchema,
    VoteResultSchema,
    ScoreResultSchema,
)

router = APIRouter(prefix="/games", tags=["votes"])


@router.post("/{game_id}/votes", response_model=VoteResultSchema)
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

    # Imposter cannot vote
    if voter.is_imposter:
        raise HTTPException(
            status_code=403,
            detail="Imposter cannot vote. Your vote does not count towards your score.",
        )

    new_vote = await vote_repo.create(
        game_id=game_id,
        voter_id=vote.voter_id,
        target_id=vote.target_id,
    )

    # Check if all non-imposter players have voted
    all_players = await player_repo.list_by_game(game_id)
    non_imposter_players = [p for p in all_players if not p.is_imposter]
    all_votes = await vote_repo.list_by_game(game_id)
    voters = {v.voter_id for v in all_votes}

    # Check if all non-imposter players have voted
    all_voted = all(p.id in voters for p in non_imposter_players)

    if all_voted:
        # All non-imposter players voted, compute scores and finish game
        score_service = ScoringService(db)
        await score_service.compute_scores(game_id)
        await game_repo.update_status(
            game_id, "finished", current_round=game.current_round
        )

    return VoteResultSchema(
        id=new_vote.id,
        game_id=new_vote.game_id,
        voter_id=new_vote.voter_id,
        target_id=new_vote.target_id,
        created_at=new_vote.created_at,
    )


@router.get("/{game_id}/votes", response_model=list[VoteResultSchema])
async def get_votes(game_id: int, db: Session = Depends(get_db)):
    """
    Get all votes for a game.
    """
    vote_repo = VoteRepository(db)
    votes = await vote_repo.list_by_game(game_id)
    return [
        VoteResultSchema(
            id=v.id,
            voter_id=v.voter_id,
            target_id=v.target_id,
            created_at=v.created_at,
        )
        for v in votes
    ]


@router.get("/{game_id}/votes/score", response_model=ScoreResultSchema)
async def get_scores(game_id: int, db: Session = Depends(get_db)):
    """
    Get computed scores for a game.
    """
    score_service = ScoringService(db)
    result = await score_service.compute_scores(game_id)
    return result


@router.post("/{game_id}/votes/score", response_model=ScoreResultSchema)
async def compute_scores(
    game_id: int,
    db: Session = Depends(get_db),
    game_repo: GameRepository = Depends(get_game_repository),
):
    """
    Compute the final scores after voting.
    """

    score_service = ScoringService(db)
    result = await score_service.compute_scores(game_id)

    # Update game status to finished
    game = await game_repo.get_by_id(game_id)
    if game and game.status != "finished":
        await game_repo.update_status(
            game_id, "finished", current_round=game.current_round
        )

    return result
