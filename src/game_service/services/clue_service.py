from game_service.repositories.clue_repo import ClueRepository

class ClueService:
    def __init__(self, session):
        self.repo = ClueRepository(session)

    async def submit_clue(self, game_id, payload):
        existing = await self.repo.get_by_player_round(
            game_id, payload.player_id, payload.round_number
        )
        if existing:
            raise ValueError("Clue already submitted")

        return await self.repo.create(
            game_id,
            payload.player_id,
            payload.round_number,
            payload.clue_word,
            payload.skipped,
        )
