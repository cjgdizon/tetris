"""Heuristic board evaluation for the bot (higher is better)."""
from dataclasses import dataclass

from tetris.engine.board import HEIGHT, WIDTH, Board


@dataclass
class Weights:
    holes: float = -8.0
    bumpiness: float = -0.4
    aggregate_height: float = -0.35
    max_height_over_10: float = -2.0  # per row above 10
    row_transitions: float = -0.3
    well: float = 0.5  # per row of depth of the deepest well, capped at 6
    tspin_slot: float = 2.0
    attack: float = 3.0  # per attack line
    tspin_clear: float = 4.0
    b2b_keep: float = 1.5
    combo: float = 0.5  # per combo step above 1
    pending_garbage: float = -0.8  # per pending line


def _holes_and_transitions(board: Board, top: int) -> tuple[int, int]:
    holes = transitions = 0
    seen = [False] * WIDTH
    for y in range(top, HEIGHT):
        row = board.cells[y]
        prev = True  # left wall counts as filled
        for x in range(WIDTH):
            filled = row[x] is not None
            if filled:
                seen[x] = True
            elif seen[x]:
                holes += 1
            if filled != prev:
                transitions += 1
            prev = filled
        if not prev:
            transitions += 1
    return holes, transitions


def _well_depth(h: list[int]) -> int:
    best = 0
    for x in range(WIDTH):
        neighbours = [h[i] for i in (x - 1, x + 1) if 0 <= i < WIDTH]
        best = max(best, min(neighbours) - h[x])
    return min(best, 6)


def _has_tspin_pocket(board: Board, top: int) -> bool:
    """A TSD-shaped pocket: 3 empty cells over a 1-wide notch, with exactly one overhang."""
    cells = board.cells
    for y in range(max(top - 3, 0), HEIGHT - 2):
        low, mid = cells[y + 2], cells[y + 1]
        for x in range(WIDTH - 2):
            if low[x] is None or low[x + 2] is None or low[x + 1] is not None:
                continue
            if mid[x] is not None or mid[x + 1] is not None or mid[x + 2] is not None:
                continue
            top_row = cells[y]
            if (top_row[x] is None) != (top_row[x + 2] is None):
                return True
    return False


def evaluate(board: Board, lines: int, tspin: str, attack: int, combo: int, b2b: bool,
             pending: int, weights: Weights = Weights()) -> float:
    """Score a board state **after** a lock and its line clears."""
    w = weights
    h = board.heights()
    top = HEIGHT - max(h)
    holes, transitions = _holes_and_transitions(board, top)
    bumpiness = sum(abs(h[i] - h[i + 1]) for i in range(WIDTH - 1))
    score = (
        w.holes * holes
        + w.bumpiness * bumpiness
        + w.aggregate_height * sum(h)
        + w.max_height_over_10 * max(0, max(h) - 10)
        + w.row_transitions * transitions
        + w.well * _well_depth(h)
        + w.attack * attack
        + w.pending_garbage * pending
    )
    if _has_tspin_pocket(board, top):
        score += w.tspin_slot
    if tspin == "full" and lines > 0:
        score += w.tspin_clear
    if b2b and lines > 0:
        score += w.b2b_keep
    score += w.combo * max(0, combo - 1)
    return score
