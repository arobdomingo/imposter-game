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
            WordPair("苹果", "香蕉"),
            WordPair("电脑", "电视"),
            WordPair("海洋", "沙漠"),
            WordPair("篮球", "足球"),
            WordPair("咖啡", "茶"),
            WordPair("山脉", "平原"),
            WordPair("猫", "狗"),
            WordPair("春天", "冬天"),
            WordPair("火车", "飞机"),
            WordPair("老师", "医生"),
        ]


def get_word_service() -> WordService:
    return WordService()
