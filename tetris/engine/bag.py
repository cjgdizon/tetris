"""Seedable 7-bag randomizer."""
import random

from tetris.engine.pieces import KINDS


class Bag:
    def __init__(self, seed: int):
        self._rng = random.Random(seed)
        self._queue: list[str] = []

    def _fill(self, n: int) -> None:
        while len(self._queue) < n:
            bag = list(KINDS)
            self._rng.shuffle(bag)
            self._queue.extend(bag)

    def next(self) -> str:
        self._fill(1)
        return self._queue.pop(0)

    def peek(self, n: int) -> list[str]:
        self._fill(n)
        return self._queue[:n]
