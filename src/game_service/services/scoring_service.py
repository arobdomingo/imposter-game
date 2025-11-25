from __future__ import annotations
from collections import defaultdict
from typing import Dict, List

from fastapi import Depends

from game_service.repositories.player_repo import get_player_repository, PlayerRepository
from game_service.repositories.vote_repo import get_vote_repository, VoteRepository
from game_service.repositories.game_repo import get_game_repository, GameRepository


class ScoringService:
    """
    Compute and apply scoring rules:
      - Correct guess -> +1 to each correct voter
      - Wrong guess -> +1 to each imposter per wrong voter
    """

    def __init__(
        self,
        player_repo: PlayerRepository,
        vote_repo: VoteRepository,
        game_repo: GameRepository,
    ):
        self.player_repo = player_repo
        self.vote_repo = vote_repo
        self.game_repo = game_repo

    def _tally(self, votes):
        tally = defaultdict(list)
        for v in votes:
            if v.target_id is not None:
                tally[v.target_id].append(v.voter_id)
        return tally

    def compute_and_apply_scores(self, game_id: int) -> dict:
        players = self.player_repo.list_by_game(game_id)
        votes = self.vote_repo.list_by_game(game_id)

        #player_map = {p.id: p for p in players}
        impostors = [p for p in players if p.is_imposter]
        impostor_ids = [p.id for p in impostors]

        tally = self._tally(votes)

        # find voted out by plurality
        voted_out = None
        max_votes = -1
        for target_id, voters in tally.items():
            if len(voters) > max_votes:
                max_votes = len(voters)
                voted_out = target_id

        score_changes: Dict[int, int] = defaultdict(int)
        correct_voters: List[int] = []
        incorrect_voters: List[int] = []

        if voted_out is not None:
            if voted_out in impostor_ids:
                # correct voters +1
                correct_voters = tally.get(voted_out, [])
                for vid in correct_voters:
                    score_changes[vid] += 1
            else:
                # wrong voters -> each wrong voter awards +1 to each impostor
                wrong_voters = []
                for target_id, voters in tally.items():
                    if target_id not in impostor_ids:
                        wrong_voters.extend(voters)
                for w in wrong_voters:
                    for imp in impostors:
                        score_changes[imp.id] += 1
                incorrect_voters = wrong_voters
        else:
            # tie/no votes -> no score changes
            pass

        # apply updates
        for pid, delta in score_changes.items():
            self.player_repo.update_score(pid, delta)

        # return snapshot
        refreshed = self.player_repo.list_by_game(game_id)
        player_scores = {str(p.id): p.score for p in refreshed}
        return {
            "player_scores": player_scores,
            "impostor_ids": impostor_ids,
            "voted_out": voted_out,
            "score_changes": {str(k): v for k, v in score_changes.items()},
            "correct_voters": correct_voters,
            "incorrect_voters": incorrect_voters,
        }


def get_scoring_service(
    player_repo: PlayerRepository = Depends(get_player_repository),
    vote_repo: VoteRepository = Depends(get_vote_repository),
    game_repo: GameRepository = Depends(get_game_repository),
) -> ScoringService:
    return ScoringService(player_repo=player_repo, vote_repo=vote_repo, game_repo=game_repo)


