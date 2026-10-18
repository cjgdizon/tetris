"""10x40 grid (rows 0-19 hidden, 20-39 visible), y down, floor is row 39."""
from tetris.engine.pieces import KICKS, SHAPES, Piece

WIDTH = 10
HEIGHT = 40
VISIBLE = 20


class Board:
    def __init__(self):
        self.cells: list[list[str | None]] = [[None] * WIDTH for _ in range(HEIGHT)]

    @classmethod
    def from_ascii(cls, rows: list[str]) -> "Board":
        b = cls()
        top = HEIGHT - len(rows)
        for i, row in enumerate(rows):
            assert len(row) == WIDTH, row
            for x, ch in enumerate(row):
                if ch != ".":
                    b.cells[top + i][x] = "X"
        return b

    def copy(self) -> "Board":
        b = Board()
        b.cells = [row[:] for row in self.cells]
        return b

    def occupied(self, x: int, y: int) -> bool:
        return not (0 <= x < WIDTH and 0 <= y < HEIGHT) or self.cells[y][x] is not None

    def fits(self, kind: str, x: int, y: int, rot: int) -> bool:
        """True if the pose is inside the board and overlaps nothing (hot path for the bot)."""
        cells = self.cells
        for cx, cy in SHAPES[kind][rot]:
            px, py = x + cx, y + cy
            if px < 0 or px >= WIDTH or py < 0 or py >= HEIGHT or cells[py][px] is not None:
                return False
        return True

    def collides(self, piece: Piece) -> bool:
        return not self.fits(piece.kind, piece.x, piece.y, piece.rot)

    def drop_distance(self, piece: Piece) -> int:
        d = 0
        while self.fits(piece.kind, piece.x, piece.y + d + 1, piece.rot):
            d += 1
        return d

    def lock(self, piece: Piece) -> None:
        for x, y in piece.cells():
            self.cells[y][x] = piece.kind

    def clear_lines(self) -> list[int]:
        full = [y for y, row in enumerate(self.cells) if all(c is not None for c in row)]
        if full:
            keep = [row for y, row in enumerate(self.cells) if y not in full]
            self.cells = [[None] * WIDTH for _ in full] + keep
        return full

    def add_garbage(self, lines: int, hole: int) -> bool:
        pushed = any(c is not None for row in self.cells[:lines] for c in row)
        rows = [["G" if x != hole else None for x in range(WIDTH)] for _ in range(lines)]
        self.cells = self.cells[lines:] + rows
        return pushed

    def is_empty(self) -> bool:
        return all(c is None for row in self.cells for c in row)

    def heights(self) -> list[int]:
        out = []
        for x in range(WIDTH):
            h = 0
            for y in range(HEIGHT):
                if self.cells[y][x] is not None:
                    h = HEIGHT - y
                    break
            out.append(h)
        return out

    def try_rotate(self, piece: Piece, direction: int) -> tuple[Piece, int] | None:
        """Rotate CW (+1) or CCW (-1) with SRS kicks; returns (piece, kick_index) or None."""
        new_rot = (piece.rot + direction) % 4
        table = "JLSTZ" if piece.kind in "JLSTZ" else piece.kind
        for idx, (dx, dy) in enumerate(KICKS[table][(piece.rot, new_rot)]):
            if self.fits(piece.kind, piece.x + dx, piece.y + dy, new_rot):
                return piece.with_rot(new_rot, piece.x + dx, piece.y + dy), idx
        return None
