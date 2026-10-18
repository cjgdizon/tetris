"""T-spin classification using the 3-corner rule."""
from tetris.engine.board import Board
from tetris.engine.pieces import Piece

# Corner offsets from the T center: (up-left, up-right, down-left, down-right)
_CORNERS = [(-1, -1), (1, -1), (-1, 1), (1, 1)]
# Indices of the two "front" corners, i.e. on the side the T points to.
_FRONT = {0: (0, 1), 1: (1, 3), 2: (2, 3), 3: (0, 2)}


def tspin_kind(board: Board, piece: Piece, rotated: bool, kick_index: int) -> str:
    """Return "none", "mini" or "full" for a T in its final (unlocked) pose."""
    if piece.kind != "T" or not rotated:
        return "none"
    cx, cy = piece.x + 1, piece.y + 1
    occ = [board.occupied(cx + dx, cy + dy) for dx, dy in _CORNERS]
    if sum(occ) < 3:
        return "none"
    if all(occ[i] for i in _FRONT[piece.rot]) or kick_index == 4:
        return "full"
    return "mini"
