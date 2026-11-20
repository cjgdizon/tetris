"""BFS over reachable piece poses to enumerate every legal final placement."""
from collections import deque
from dataclasses import dataclass

from tetris.engine.board import HEIGHT, Board
from tetris.engine.pieces import SPAWN, Piece
from tetris.engine.player import Action
from tetris.engine.tspin import TSpin, tspin_kind


@dataclass(frozen=True)
class Placement:
    piece: Piece  # final grounded pose
    actions: tuple[Action, ...]  # path from spawn, ending with HARD
    tspin: TSpin


def find_placements(board: Board, kind: str, start: Piece | None = None) -> list[Placement]:
    """All distinct grounded poses reachable from `start` (default: spawn), each with its shortest path."""
    start = start or Piece(kind, SPAWN[0], SPAWN[1], 0)
    if board.collides(start):
        return []
    track_kick = kind == "T"  # only T cares how its last rotation happened
    s0 = (start.x, start.y, start.rot, None)
    prev = {s0: None}
    queue = deque([s0])
    finals: dict[tuple, Placement] = {}

    # Rows this far above the stack are empty, so one SOFT macro-step can fall through them.
    y_margin = HEIGHT - max(board.heights()) - 5

    def push(state, parent, acts):
        if state not in prev:
            prev[state] = (parent, acts)
            queue.append(state)

    while queue:
        state = queue.popleft()
        x, y, rot, kick = state
        if not board.fits(kind, x, y + 1, rot):
            piece = Piece(kind, x, y, rot)
            spin = tspin_kind(board, piece, kick is not None, kick or 0)
            key = (frozenset(piece.cells()), spin)
            if key not in finals:
                path, cur = [], state
                while prev[cur] is not None:
                    cur, acts = prev[cur]
                    path.extend(reversed(acts))
                finals[key] = Placement(piece, tuple(reversed(path)) + (Action.HARD,), spin)
        for action, dx in ((Action.LEFT, -1), (Action.RIGHT, 1)):
            if board.fits(kind, x + dx, y, rot):
                push((x + dx, y, rot, None), state, (action,))
        if board.fits(kind, x, y + 1, rot):
            k = max(1, y_margin - y)
            push((x, y + k, rot, None), state, (Action.SOFT,) * k)
        if kind == "O":
            continue
        cur = Piece(kind, x, y, rot)
        for action, d in ((Action.CW, 1), (Action.CCW, -1)):
            res = board.try_rotate(cur, d)
            if res is not None:
                np_, k = res
                push((np_.x, np_.y, np_.rot, k if track_kick else None), state, (action,))
    return list(finals.values())


def drop_placements(board: Board, kind: str) -> list[Piece]:
    """Cheap placements for lookahead: every rotation x column straight hard drop (no tucks/spins)."""
    seen: set[frozenset] = set()
    out: list[Piece] = []
    y0 = max(0, HEIGHT - max(board.heights()) - 4)  # start just above the stack
    for rot in range(4):
        for x in range(-2, 10):
            piece = Piece(kind, x, y0, rot)
            if board.collides(piece):
                continue
            piece = piece.moved(0, board.drop_distance(piece))
            key = frozenset(piece.cells())
            if key not in seen:
                seen.add(key)
                out.append(piece)
    return out
