"""A battle between two players: shared pieces, garbage routing, rounds, best-of-N."""
import random
from collections.abc import Sequence

from tetris.engine.attack import Batch
from tetris.engine.player import Action, LockResult, Player

FRAMES_PER_LEVEL = 30 * 60
MAX_LEVEL = 15


def gravity_for_level(level: int) -> float:
    """Frames per row at a guideline level."""
    return 60 * (0.8 - (level - 1) * 0.007) ** (level - 1)


class Match:
    def __init__(self, seed: int, best_of: int = 3):
        self.seed = seed
        self.best_of = best_of
        self.rng = random.Random(seed)
        self.wins = [0, 0]
        self.match_winner: int | None = None
        self._round = 0
        self._new_round()

    def _new_round(self) -> None:
        s = self.seed * 1000 + self._round
        self.players = (Player(s), Player(s))
        self.frame = 0
        self.round_over = False
        self.round_winner: int | None = None
        self.last_locks: tuple[LockResult | None, LockResult | None] = (None, None)
        self._apply_gravity()

    @property
    def level(self) -> int:
        return min(MAX_LEVEL, 1 + self.frame // FRAMES_PER_LEVEL)

    def _apply_gravity(self) -> None:
        g = gravity_for_level(self.level)
        for p in self.players:
            p.gravity_frames = g

    def next_round(self) -> None:
        self._round += 1
        self._new_round()

    def step(self, actions0: Sequence[Action], actions1: Sequence[Action]) -> None:
        if self.round_over:
            return
        locks = (self.players[0].step(actions0), self.players[1].step(actions1))
        for i, r in enumerate(locks):
            if r is not None and r.sent > 0:
                self.players[1 - i].pending.append(Batch(r.sent, self.rng.randrange(10)))
        self.last_locks = locks
        self.frame += 1
        self._apply_gravity()
        alive = [p.alive for p in self.players]
        if all(alive):
            return
        self.round_over = True
        if any(alive):
            self.round_winner = alive.index(True)
            self.wins[self.round_winner] += 1
            if self.wins[self.round_winner] >= self.best_of // 2 + 1:
                self.match_winner = self.round_winner
