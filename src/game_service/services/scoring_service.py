from game_service.repositories.vote_repo import VoteRepository
from game_service.repositories.player_repo import PlayerRepository
from game_service.schemas.vote import ScoreResultSchema


class ScoringService:
    def __init__(self, session):
        self.session = session
        self.player_repo = PlayerRepository(session)
        self.vote_repo = VoteRepository(session)

    async def compute_scores(self, game_id: int) -> ScoreResultSchema:
        players = await self.player_repo.list_players(game_id)
        votes = await self.vote_repo.list_by_game(game_id)

        impostors = [p for p in players if p.is_imposter]
        impostor_ids = [p.id for p in impostors]

        # start all scores at 0
        score_map = {str(p.id): 0 for p in players}

        # Score votes according to intended rules
        for v in votes:
            if v.target_id in impostor_ids:
                # Correct guess → voter +1
                score_map[str(v.voter_id)] += 1
            else:
                # Wrong guess → each impostor +1
                for imp_id in impostor_ids:
                    score_map[str(imp_id)] += 1

        return ScoreResultSchema(
            game_id=game_id,
            impostor_ids=impostor_ids,
            player_scores=score_map,
        )
