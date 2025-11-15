import pytest
from sqlalchemy.exc import IntegrityError

from game_service.repositories import (
    LobbyRepository,
    GameRepository,
    PlayerRepository,
    ClueRepository,
    VoteRepository,
)


@pytest.mark.asyncio
async def test_lobby_repository_create_and_get(session):
    repo = LobbyRepository(session)
    lobby = await repo.create(code="ABCD", host_id=1)
    fetched = await repo.get_by_code("ABCD")
    assert fetched is not None
    assert fetched.id == lobby.id
    assert fetched.status == "waiting"

    await repo.update_status(lobby.id, "playing")
    updated = await repo.get_by_id(lobby.id)
    assert updated.status == "playing"


@pytest.mark.asyncio
async def test_game_repository(session):
    lobby_repo = LobbyRepository(session)
    lobby = await lobby_repo.create("ROOM1", host_id=1)

    repo = GameRepository(session)
    game = await repo.create(lobby_id=lobby.id, mode="aware")
    assert game.status == "waiting"

    await repo.update_status(game.id, "clue", current_round=2)
    updated = await repo.get_by_id(game.id)
    assert updated.status == "clue"
    assert updated.current_round == 2

    active = await repo.get_active_by_lobby(lobby.id)
    assert active is not None
    assert active.id == game.id


@pytest.mark.asyncio
async def test_player_repository_add_and_unique_constraints(session, users):
    lobby_repo = LobbyRepository(session)
    lobby = await lobby_repo.create("ROOM2", host_id=users[0].id)
    game_repo = GameRepository(session)
    game = await game_repo.create(lobby_id=lobby.id, mode="aware")

    repo = PlayerRepository(session)
    player = await repo.add_player(game.id, users[0].id, seat_no=1)
    assert player.seat_no == 1

    with pytest.raises(IntegrityError):
        await repo.add_player(game.id, users[0].id, seat_no=2)
    session.rollback()

    with pytest.raises(IntegrityError):
        await repo.add_player(game.id, users[1].id, seat_no=1)
    session.rollback()

    players = await repo.list_by_game(game.id)
    assert len(players) == 1

    await repo.update_score(player.id, 2)
    updated = await repo.get_by_id(player.id)
    assert updated.score == 2


@pytest.mark.asyncio
async def test_clue_repository(session, users):
    lobby_repo = LobbyRepository(session)
    lobby = await lobby_repo.create("ROOM3", host_id=users[0].id)
    game_repo = GameRepository(session)
    game = await game_repo.create(lobby_id=lobby.id, mode="aware")

    player_repo = PlayerRepository(session)
    player = await player_repo.add_player(game.id, users[0].id, seat_no=1)

    repo = ClueRepository(session)
    clue = await repo.create(game.id, player.id, round_number=1, clue_word="水果")
    assert clue.clue_word == "水果"

    fetched = await repo.get_by_player_round(game.id, player.id, 1)
    assert fetched.id == clue.id

    with pytest.raises(IntegrityError):
        await repo.create(game.id, player.id, round_number=1, clue_word="重复")
    session.rollback()

    clues = await repo.list_by_game(game.id)
    assert len(clues) == 1


@pytest.mark.asyncio
async def test_vote_repository(session, users):
    lobby_repo = LobbyRepository(session)
    lobby = await lobby_repo.create("ROOM4", host_id=users[0].id)
    game_repo = GameRepository(session)
    game = await game_repo.create(lobby_id=lobby.id, mode="aware")

    player_repo = PlayerRepository(session)
    players = [
        await player_repo.add_player(game.id, user.id, seat_no=i + 1)
        for i, user in enumerate(users[:2])
    ]

    repo = VoteRepository(session)
    vote = await repo.create(game.id, players[0].id, players[1].id)
    assert vote.target_id == players[1].id

    with pytest.raises(IntegrityError):
        await repo.create(game.id, players[0].id, players[1].id)
    session.rollback()

    votes = await repo.list_by_game(game.id)
    assert len(votes) == 1

    await repo.clear_game_votes(game.id)
    votes_after = await repo.list_by_game(game.id)
    assert votes_after == []
