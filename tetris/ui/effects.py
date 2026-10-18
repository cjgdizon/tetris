"""Short-lived visual effects driven by lock results. No pygame: pure counters."""
import random

from tetris.engine.player import LockResult

SHAKE_FRAMES = 20
FLASH_FRAMES = 6
PULSE_FRAMES = 12
BIG_ATTACK = 4


class Effects:
    def __init__(self, seed: int = 0):
        self._rng = random.Random(seed)
        self._shake = 0
        self._amp = 0
        self._flash: list[tuple[list[int], int]] = [([], 0), ([], 0)]
        self._pulse = [0, 0]
        self._pending = [0, 0]

    def on_locks(self, locks: tuple[LockResult | None, LockResult | None]) -> None:
        for side, r in enumerate(locks):
            if r is None:
                continue
            if r.sent >= BIG_ATTACK:
                self._shake = SHAKE_FRAMES
                self._amp = min(r.sent, 10)
            if r.cleared_rows:
                self._flash[side] = (list(r.cleared_rows), FLASH_FRAMES)

    def on_pending(self, totals: tuple[int, int]) -> None:
        """Call each frame with each side's pending-garbage line count."""
        for side in (0, 1):
            if totals[side] > self._pending[side]:
                self._pulse[side] = PULSE_FRAMES
            self._pending[side] = totals[side]

    def update(self) -> None:
        self._shake = max(0, self._shake - 1)
        self._pulse = [max(0, p - 1) for p in self._pulse]
        self._flash = [(rows, n - 1) if n > 1 else ([], 0) for rows, n in self._flash]

    def shake_offset(self) -> tuple[int, int]:
        if self._shake == 0:
            return (0, 0)
        mag = max(1, self._amp * self._shake // SHAKE_FRAMES)
        return (self._rng.randint(-mag, mag), self._rng.randint(-mag, mag))

    def flash_rows(self, side: int) -> list[int]:
        return self._flash[side][0]

    def meter_pulse(self, side: int) -> float:
        return self._pulse[side] / PULSE_FRAMES
