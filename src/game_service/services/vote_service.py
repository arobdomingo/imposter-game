from game_service.repositories.vote_repo import VoteRepository

class VoteService:

    def __init__(self, session):
        self.repo = VoteRepository(session)

    async def submit_vote(self, game_id, voter_id, target_id):
        return await self.repo.submit_vote(game_id, voter_id, target_id)
