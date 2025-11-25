"""import pytest
from httpx import AsyncClient

from src.admin.main import app

from game_service.repositories.lobby_repo import LobbyRepository
from game_service.repositories.game_repo import GameRepository
from game_service.repositories.player_repo import PlayerRepository
from game_service.repositories.clue_repo import ClueRepository
from game_service.repositories.vote_repo import VoteRepository

@pytest.mark.asyncio
async def test_clue_submission_flow(session, users, monkeypatch):

    lobby_repo = LobbyRepository(session)
    game_repo = GameRepository(session)
    player_repo = PlayerRepository(session)
    clue_repo = ClueRepository(session)

    # Create lobby
    lobby = await lobby_repo.create(code="TEST01", host_id=users[0].id)

    game = await game_repo.create(lobby_id=lobby.id, mode="aware")

    # Add 4 players
    p1 = await player_repo.add_player(game.id, users[0].id, seat_no=1)
    p2 = await player_repo.add_player(game.id, users[1].id, seat_no=2)
    p3 = await player_repo.add_player(game.id, users[2].id, seat_no=3)
    p4 = await player_repo.add_player(game.id, users[3].id, seat_no=4)

    client = AsyncClient(app=app, base_url="http://test")

    # Submit clue
    response = await client.post(
        f"/games/{game.id}/clues/submit",
        json={
            "player_id": p1.id,
            "round_number": 1,
            "clue_word": "fruit",
            "skipped": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["player_id"] == p1.id
    assert data["clue_word"] == "fruit"

    stored = await clue_repo.get_by_player_round(game.id, p1.id, 1)
    assert stored.clue_word == "fruit"


@pytest.mark.asyncio
async def test_vote_submission_and_scoring(session, users):


    lobby_repo = LobbyRepository(session)
    game_repo = GameRepository(session)
    player_repo = PlayerRepository(session)
    clue_repo = ClueRepository(session)
    vote_repo = VoteRepository(session)

    # Create lobby + game
    lobby = await lobby_repo.create("TEST02", host_id=users[0].id)
    game = await game_repo.create(lobby_id=lobby.id, mode="aware")

    # Create players (P1 is impostor)
    p1 = await player_repo.add_player(game.id, users[0].id, seat_no=1, is_imposter=True)
    p2 = await player_repo.add_player(game.id, users[1].id, seat_no=2)
    p3 = await player_repo.add_player(game.id, users[2].id, seat_no=3)
    p4 = await player_repo.add_player(game.id, users[3].id, seat_no=4)

    # Create dummy clue entries
    for p in [p1, p2, p3, p4]:
        await clue_repo.create(game.id, p.id, round_number=1, clue_word="test")

    client = AsyncClient(app=app, base_url="http://test")

    # Voting
    await client.post(f"/games/{game.id}/votes", json={"voter_id": p2.id, "target_id": p1.id})
    await client.post(f"/games/{game.id}/votes", json={"voter_id": p3.id, "target_id": p2.id})
    await client.post(f"/games/{game.id}/votes", json={"voter_id": p4.id, "target_id": p3.id})

    # Score round
    res_score = await client.post(f"/games/{game.id}/votes/score")

    assert res_score.status_code == 200
    scoring = res_score.json()

    assert scoring["player_scores"][str(p2.id)] == 1
    assert scoring["player_scores"][str(p1.id)] == 2
    assert scoring["player_scores"][str(p3.id)] == 0
    assert scoring["player_scores"][str(p4.id)] == 0

    # DB scores updated?
    updated_p1 = await player_repo.get_by_id(p1.id)
    updated_p2 = await player_repo.get_by_id(p2.id)

    assert updated_p1.score == 2
    assert updated_p2.score == 1"""
