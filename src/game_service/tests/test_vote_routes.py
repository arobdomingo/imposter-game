import pytest
from httpx import AsyncClient

from admin.main import app  # FastAPI app entrypoint

from game_service.repositories.lobby_repo import LobbyRepository
from game_service.repositories.game_repo import GameRepository
from game_service.repositories.player_repo import PlayerRepository
from game_service.repositories.clue_repo import ClueRepository


@pytest.mark.asyncio
async def test_vote_and_scoring_flow(session, users):
    lobby_repo = LobbyRepository(session)
    game_repo = GameRepository(session)
    player_repo = PlayerRepository(session)
    clue_repo = ClueRepository(session)
    #vote_repo = VoteRepository(session)

    lobby = await lobby_repo.create(code="ROOM-TEST", host_id=users[0].id)
    game = await game_repo.create(lobby_id=lobby.id, mode="aware")

    # create players (p1 impostor for test)
    p1 = await player_repo.add_player(game.id, users[0].id, seat_no=1, is_imposter=True)
    p2 = await player_repo.add_player(game.id, users[1].id, seat_no=2)
    p3 = await player_repo.add_player(game.id, users[2].id, seat_no=3)
    p4 = await player_repo.add_player(game.id, users[3].id, seat_no=4)

    # all players submit clues
    for p in [p1, p2, p3, p4]:
        await clue_repo.create(game.id, p.id, round_number=1, clue_word="x")

    async with AsyncClient(app=app, base_url="http://test") as client:
        # p2 correct
        r1 = await client.post(
            f"/games/{game.id}/votes",
            json={"game_id": game.id, "voter_id": p2.id, "target_id": p1.id},
        )
        assert r1.status_code == 200

        # p3 wrong
        r2 = await client.post(
            f"/games/{game.id}/votes",
            json={"game_id": game.id, "voter_id": p3.id, "target_id": p2.id},
        )
        assert r2.status_code == 200

        # p4 wrong
        r3 = await client.post(
            f"/games/{game.id}/votes",
            json={"game_id": game.id, "voter_id": p4.id, "target_id": p3.id},
        )
        assert r3.status_code == 200

        # finalize scoring
        rscore = await client.post(f"/games/{game.id}/votes/score")
        assert rscore.status_code == 200

        data = rscore.json()

        # ✅ updated assertions
        assert data["player_scores"][str(p2.id)] == 1  # correct voter got +1
        assert data["player_scores"][str(p1.id)] == 2  # impostor got +2
        assert p1.id in data["impostor_ids"]           # impostor list contains p1

