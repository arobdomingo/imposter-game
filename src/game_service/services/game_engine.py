from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from fastapi import Depends

from game_service.repositories import (
    LobbyRepository,
    GameRepository,
    PlayerRepository,
    ClueRepository,
    VoteRepository,
    get_lobby_repository,
    get_game_repository,
    get_player_repository,
    get_clue_repository,
    get_vote_repository,
)
from game_service.services.word_service import WordService, get_word_service


@dataclass
class GameEngineConfig:
    max_players: int = 4
    total_rounds: int = 3


class GameEngine:
    """Core game coordinator for lobby/game lifecycle."""

    def __init__(
        self,
        lobby_repo: LobbyRepository,
        game_repo: GameRepository,
        player_repo: PlayerRepository,
        clue_repo: ClueRepository,
        vote_repo: VoteRepository,
        word_service: WordService,
        config: GameEngineConfig | None = None,
    ) -> None:
        self.lobby_repo = lobby_repo
        self.game_repo = game_repo
        self.player_repo = player_repo
        self.clue_repo = clue_repo
        self.vote_repo = vote_repo
        self.word_service = word_service
        self.config = config or GameEngineConfig()

    async def start_game(
        self, lobby_id: int, player_user_ids: Sequence[int], mode: str
    ) -> int:
        """Create a game, assign players, and return game id."""
        game = await self.game_repo.create(lobby_id=lobby_id, mode=mode)
        await self.lobby_repo.update_status(lobby_id, "playing")

        common_word, impostor_word = self.word_service.get_words(mode)
        impostor_index = await self._choose_impostor_index(player_user_ids)

        for seat_no, user_id in enumerate(player_user_ids, start=1):
            is_imposter = seat_no - 1 == impostor_index
            word = common_word if not is_imposter else impostor_word
            await self.player_repo.add_player(
                game_id=game.id,
                user_id=user_id,
                seat_no=seat_no,
                is_imposter=is_imposter,
                word=word,
            )

        return game.id

    async def _choose_impostor_index(self, player_user_ids: Sequence[int]) -> int:
        from random import randint

        return randint(0, len(player_user_ids) - 1)


async def get_game_engine(
    lobby_repo: LobbyRepository = Depends(get_lobby_repository),
    game_repo: GameRepository = Depends(get_game_repository),
    player_repo: PlayerRepository = Depends(get_player_repository),
    clue_repo: ClueRepository = Depends(get_clue_repository),
    vote_repo: VoteRepository = Depends(get_vote_repository),
    word_service: WordService = Depends(get_word_service),
) -> GameEngine:
    return GameEngine(
        lobby_repo=lobby_repo,
        game_repo=game_repo,
        player_repo=player_repo,
        clue_repo=clue_repo,
        vote_repo=vote_repo,
        word_service=word_service,
    )
