"""Frame-based key handling: DAS/ARR for movement, SDF-paced soft drop, edge-triggered keys."""
from dataclasses import dataclass

from tetris.engine.player import Action

_DIRS = (Action.LEFT, Action.RIGHT)
_EDGE_ORDER = (Action.CCW, Action.CW, Action.HOLD)  # HARD is emitted last
_INSTANT_SLIDE = 10


@dataclass
class Handling:
    das: int = 10
    arr: int = 2
    sdf: float = 20.0


class InputHandler:
    def __init__(self, handling: Handling):
        self.h = handling
        self.reset()

    def reset(self) -> None:
        self._prev: set[Action] = set()
        self._count: dict[Action, int] = {}
        self._active: Action | None = None
        self._soft_acc = 0.0

    def update(self, held: set[Action], gravity_frames: float) -> list[Action]:
        """Call once per frame with the currently held actions; returns actions to apply."""
        pressed = held - self._prev
        out: list[Action] = []

        for d in _DIRS:
            if d in held:
                self._count[d] = 0 if d in pressed else self._count.get(d, 0) + 1
            else:
                self._count.pop(d, None)
        for d in _DIRS:  # most recently pressed direction wins
            if d in pressed:
                self._active = d
        if self._active not in held:
            self._active = next((d for d in _DIRS if d in held), None)
        if self._active is not None:
            d, c = self._active, self._count[self._active]
            if c == 0:
                out.append(d)
            elif c >= self.h.das:
                if self.h.arr == 0:
                    out.extend([d] * _INSTANT_SLIDE)
                elif (c - self.h.das) % self.h.arr == 0:
                    out.append(d)

        out.extend(a for a in _EDGE_ORDER if a in pressed)

        if Action.SOFT in held:
            self._soft_acc = 1.0 if Action.SOFT in pressed else self._soft_acc + self.h.sdf / gravity_frames
            if self._soft_acc >= 1.0 - 1e-9:
                out.append(Action.SOFT)
                self._soft_acc = 0.0
        else:
            self._soft_acc = 0.0

        if Action.HARD in pressed:
            out.append(Action.HARD)
        self._prev = set(held)
        return out
