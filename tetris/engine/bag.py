"""Seedable 7-bag randomizer."""
from collections import deque
from itertools import islice
import random

from tetris.engine.pieces import KINDS


class Bag:
    def __init__(self, seed: int):
        self._rng = random.Random(seed)
        self._queue: deque[str] = deque()

    def _fill(self, n: int) -> None:
        while len(self._queue) < n:
            bag = list(KINDS)
            self._rng.shuffle(bag)
            self._queue.extend(bag)

    def next(self) -> str:
        self._fill(1)
        return self._queue.popleft()

    def peek(self, n: int) -> list[str]:
        self._fill(n)
        return list(islice(self._queue, n))
