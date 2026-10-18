"""One player's state machine: movement, gravity, lock delay, hold."""
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum, auto

from tetris.engine.attack import Batch, attack_lines, cancel, is_difficult, land
from tetris.engine.bag import Bag
from tetris.engine.board import VISIBLE, Board
from tetris.engine.pieces import SPAWN, Piece
from tetris.engine.tspin import tspin_kind

LOCK_DELAY = 30
MAX_RESETS = 15


class Action(Enum):
    LEFT = auto()
    RIGHT = auto()
    SOFT = auto()  # move down exactly one row
    HARD = auto()
    CW = auto()
    CCW = auto()
    HOLD = auto()


@dataclass
class LockResult:
    lines: int
    tspin: str
    sent: int
    cancelled: int
    perfect_clear: bool
    cleared_rows: list[int] = field(default_factory=list)
    garbage_landed: int = 0


class Player:
    def __init__(self, seed: int, gravity_frames: float = 60.0):
        self.board = Board()
        self.bag = Bag(seed)
        self.pending: list[Batch] = []
        self.alive = True
        self.pieces_locked = 0
        self.gravity_frames = gravity_frames
        self.hold_kind: str | None = None
        self.held = False
        self.last_move_rotation = False
        self.last_kick = 0
        self.combo = 0
        self.b2b = False
        self.piece: Piece | None = None
        self._spawn(self.bag.next())

    # -- piece lifecycle -------------------------------------------------
    def _spawn(self, kind: str) -> None:
        self.piece = Piece(kind, SPAWN[0], SPAWN[1], 0)
        self._acc = 0.0
        self._timer = 0
        self._resets = 0
        self._lowest = self.piece.y
        self.last_move_rotation = False
        self.last_kick = 0
        if self.board.collides(self.piece):
            self.alive = False

    def _grounded(self) -> bool:
        return self.board.collides(self.piece.moved(0, 1))

    def _lock_piece(self) -> LockResult:
        """Lock the active piece, resolve clears/attack/garbage, spawn the next piece."""
        piece = self.piece
        tspin = tspin_kind(self.board, piece, self.last_move_rotation, self.last_kick)
        self.board.lock(piece)
        self.pieces_locked += 1
        self.held = False
        lock_out = all(y < VISIBLE for _, y in piece.cells())
        rows = self.board.clear_lines()
        lines = len(rows)
        perfect = lines > 0 and self.board.is_empty()
        raw = attack_lines(lines, tspin, self.b2b, self.combo, perfect)
        sent = cancel(self.pending, raw)
        landed = 0
        if lines > 0:
            self.b2b = is_difficult(lines, tspin)
            self.combo += 1
        else:
            self.combo = 0
            for batch in land(self.pending, 8):
                landed += batch.lines
                if self.board.add_garbage(batch.lines, batch.hole):
                    self.alive = False
        if lock_out:
            self.alive = False
        if self.alive:
            self._spawn(self.bag.next())
        return LockResult(lines, tspin, sent, raw - sent, perfect, rows, landed)

    # -- movement --------------------------------------------------------
    def _after_move(self) -> None:
        if self.piece.y > self._lowest:
            self._lowest = self.piece.y
            self._resets = 0
            self._timer = 0
        elif self._grounded() and self._resets < MAX_RESETS:
            self._resets += 1
            self._timer = 0

    def _try_move(self, dx: int, dy: int) -> bool:
        new = self.piece.moved(dx, dy)
        if self.board.collides(new):
            return False
        self.piece = new
        self.last_move_rotation = False
        self._after_move()
        return True

    def _try_rotate(self, direction: int) -> None:
        res = self.board.try_rotate(self.piece, direction)
        if res is None:
            return
        self.piece, self.last_kick = res
        self.last_move_rotation = True
        self._after_move()

    def _hold(self) -> None:
        if self.held:
            return
        cur = self.piece.kind
        nxt = self.hold_kind if self.hold_kind is not None else self.bag.next()
        self.hold_kind = cur
        self._spawn(nxt)
        self.held = True

    # -- frame step ------------------------------------------------------
    def step(self, actions: Sequence[Action]):
        if not self.alive or self.piece is None:
            return None
        for a in actions:
            if a is Action.LEFT:
                self._try_move(-1, 0)
            elif a is Action.RIGHT:
                self._try_move(1, 0)
            elif a is Action.SOFT:
                self._try_move(0, 1)
            elif a is Action.CW:
                self._try_rotate(1)
            elif a is Action.CCW:
                self._try_rotate(-1)
            elif a is Action.HOLD:
                self._hold()
                if not self.alive:
                    return None
            elif a is Action.HARD:
                d = self.board.drop_distance(self.piece)
                if d:
                    self.piece = self.piece.moved(0, d)
                    self.last_move_rotation = False
                return self._lock_piece()
        self._acc += 1.0 / self.gravity_frames
        while self._acc >= 1.0:
            self._acc -= 1.0
            if not self._try_move(0, 1):
                self._acc = 0.0
                break
        if self._grounded():
            self._timer += 1
            if self._timer >= LOCK_DELAY:
                return self._lock_piece()
        else:
            self._timer = 0
        return None

    # -- queries ---------------------------------------------------------
    def next_kinds(self, n: int = 5) -> list[str]:
        return self.bag.peek(n)

    def ghost(self) -> Piece | None:
        if self.piece is None:
            return None
        return self.piece.moved(0, self.board.drop_distance(self.piece))
