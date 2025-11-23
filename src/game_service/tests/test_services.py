import pytest

from game_service.repositories import (
    LobbyRepository,
    GameRepository,
    PlayerRepository,
    ClueRepository,
    VoteRepository,
)
from game_service.services import WordService, WordPair, GameEngine, GameEngineConfig


def test_word_service_modes():
    service = WordService([WordPair("common", "impostor")])
    common, impostor = service.get_words(mode="aware")
    assert common == "common"
    assert impostor is None

    common2, impostor2 = service.get_words(mode="unaware")
    assert common2 == "common"
    assert impostor2 == "impostor"


@pytest.mark.asyncio
async def test_game_engine_start_game(session, users):
    lobby_repo = LobbyRepository(session)
    game_repo = GameRepository(session)
    player_repo = PlayerRepository(session)
    clue_repo = ClueRepository(session)
    vote_repo = VoteRepository(session)

    lobby = await lobby_repo.create("ROOM5", host_id=users[0].id)

    class DeterministicEngine(GameEngine):
        async def _choose_impostor_index(self, player_user_ids):
            return 1

    engine = DeterministicEngine(
        lobby_repo=lobby_repo,
        game_repo=game_repo,
        player_repo=player_repo,
        clue_repo=clue_repo,
        vote_repo=vote_repo,
        word_service=WordService([WordPair("common", "impostor word")]),
        config=GameEngineConfig(max_players=4, total_rounds=3),
    )

    player_ids = [u.id for u in users[:3]]
    game_id = await engine.start_game(lobby.id, player_ids, mode="unaware")

    game = await game_repo.get_by_id(game_id)
    assert game is not None
    assert game.lobby_id == lobby.id

    lobby_refreshed = await lobby_repo.get_by_id(lobby.id)
    assert lobby_refreshed.status == "playing"

    players = await player_repo.list_by_game(game_id)
    assert len(players) == 3

    impostor = [p for p in players if p.is_imposter][0]
    assert impostor.user_id == users[1].id
    assert impostor.word == "impostor word"

    crew_words = {p.word for p in players if not p.is_imposter}
    assert crew_words == {"common"}
