from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence


@dataclass
class WordPair:
    common: str
    impostor: str


class WordService:
    """Simple word provider for game rounds."""

    def __init__(self, word_pairs: Sequence[WordPair] | None = None) -> None:
        if word_pairs is None:
            word_pairs = self._default_pairs()
        self._word_pairs = list(word_pairs)

    def get_words(self, mode: str = "aware") -> tuple[str, str | None]:
        pair = random.choice(self._word_pairs)
        if mode == "aware":
            return pair.common, None
        return pair.common, pair.impostor

    @staticmethod
    def _default_pairs() -> list[WordPair]:
        return [
            WordPair("apple", "banana"),
            WordPair("computer", "television"),
            WordPair("ocean", "desert"),
            WordPair("basketball", "football"),
            WordPair("coffee", "tea"),
            WordPair("mountain", "plain"),
            WordPair("cat", "dog"),
            WordPair("spring", "winter"),
            WordPair("train", "airplane"),
            WordPair("teacher", "doctor"),
        ]


def get_word_service() -> WordService:
    return WordService()
