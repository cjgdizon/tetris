"""Tetromino shapes, SRS kick data and the immutable Piece pose."""
from dataclasses import dataclass
from typing import Literal

Kind = Literal["I", "O", "T", "S", "Z", "J", "L"]
KINDS = "IOTSZJL"
SPAWN = (3, 18)

_BASE = {
    "T": ([(1, 0), (0, 1), (1, 1), (2, 1)], 3),
    "S": ([(1, 0), (2, 0), (0, 1), (1, 1)], 3),
    "Z": ([(0, 0), (1, 0), (1, 1), (2, 1)], 3),
    "J": ([(0, 0), (0, 1), (1, 1), (2, 1)], 3),
    "L": ([(2, 0), (0, 1), (1, 1), (2, 1)], 3),
    "I": ([(0, 1), (1, 1), (2, 1), (3, 1)], 4),
    "O": ([(1, 0), (2, 0), (1, 1), (2, 1)], 4),
}


def _build_shapes():
    shapes = {}
    for kind, (cells, n) in _BASE.items():
        states = [list(cells)]
        for _ in range(3):
            cells = [(n - 1 - y, x) for x, y in cells]  # rotate CW inside the box
            states.append(list(cells))
        shapes[kind] = [list(states[0])] * 4 if kind == "O" else states
    return shapes


SHAPES = _build_shapes()

# Tetris-guideline SRS kick data, written y-up, converted to y-down below.
_JLSTZ_UP = {
    (0, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (1, 0): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
    (1, 2): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
    (2, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (2, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
    (3, 2): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (3, 0): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (0, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
}
_I_UP = {
    (0, 1): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
    (1, 0): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
    (1, 2): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
    (2, 1): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
    (2, 3): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
    (3, 2): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
    (3, 0): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
    (0, 3): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
}


def _down(table):
    return {k: [(dx, -dy) for dx, dy in v] for k, v in table.items()}


_O_KICKS = {(a, b): [(0, 0)] for a in range(4) for b in range(4) if a != b}
KICKS = {"JLSTZ": _down(_JLSTZ_UP), "I": _down(_I_UP), "O": _O_KICKS}


@dataclass(frozen=True)
class Piece:
    kind: Kind
    x: int
    y: int
    rot: int = 0

    def cells(self) -> list[tuple[int, int]]:
        return [(self.x + cx, self.y + cy) for cx, cy in SHAPES[self.kind][self.rot]]

    def moved(self, dx: int, dy: int) -> "Piece":
        return Piece(self.kind, self.x + dx, self.y + dy, self.rot)

    def with_rot(self, rot: int, x: int, y: int) -> "Piece":
        return Piece(self.kind, x, y, rot)
