"""The bot: pick a placement (current piece + hold, short lookahead), then play it at a human pace."""
from collections import deque
import math

from tetris.bot.evaluate import Weights, evaluate
from tetris.bot.placements import drop_placements, find_placements
from tetris.engine.attack import resolve_clear
from tetris.engine.board import Board
from tetris.engine.pieces import Piece
from tetris.engine.player import Action, Player
from tetris.engine.tspin import TSpin

BEAM = 5
FPS = 60


class Bot:
    def __init__(self, pps: float = 2.5, weights: Weights | None = None):
        self.pps = pps
        self.w = weights or Weights()
        self._player: Player | None = None  # the player the current plan was made for
        self._for: int | None = None  # ...and its pieces_locked at that time
        self._chunks: deque[list[Action]] = deque()
        self._wait = 0.0
        self._gap = 1.0
        self._start: Piece | None = None
        self._first = True

    # -- evaluation ------------------------------------------------------
    def _after(self, board: Board, piece: Piece, tspin: TSpin, b2b: bool, combo: int, pending: int):
        b = board.copy()
        new_b2b, new_combo, rows, attack, _, _ = resolve_clear(b, piece, tspin, b2b, combo)
        lines = len(rows)
        if lines:
            pending = max(0, pending - attack)
        value = evaluate(b, lines, tspin, attack, new_combo, new_b2b, pending, self.w)
        return b, value, new_b2b, new_combo, pending

    def _choose(self, player: Player) -> list[Action]:
        board, cur = player.board, player.piece
        queue = player.next_kinds(3)
        pending = sum(b.lines for b in player.pending)
        cands = [(pl, list(pl.actions), queue) for pl in find_placements(board, cur.kind, start=cur)]
        if not player.held:
            if player.hold_kind is None:
                alt, rest = queue[0], queue[1:]
            else:
                alt, rest = player.hold_kind, queue
            cands += [(pl, [Action.HOLD, *pl.actions], rest) for pl in find_placements(board, alt)]
        if not cands:
            return [Action.HARD]
        scored = []
        for pl, actions, rest in cands:
            b, v, b2b, combo, pend = self._after(board, pl.piece, pl.tspin, player.b2b, player.combo, pending)
            scored.append((v, actions, b, rest, b2b, combo, pend))
        scored.sort(key=lambda t: t[0], reverse=True)
        best_total, best_actions = -math.inf, scored[0][1]
        for v, actions, b, rest, b2b, combo, pend in scored[:BEAM]:
            second = 0.0
            if rest:
                options = drop_placements(b, rest[0])
                if options:
                    second = max(self._after(b, p, "none", b2b, combo, pend)[1] for p in options)
            if v + second > best_total:
                best_total, best_actions = v + second, actions
        return best_actions

    # -- pacing ----------------------------------------------------------
    def _plan(self, player: Player) -> None:
        actions = self._choose(player)
        chunks: list[list[Action]] = []
        for a in actions:
            if a is Action.SOFT and chunks:
                chunks[-1].append(a)  # soft-drop runs share the previous frame
            else:
                chunks.append([a])
        budget = FPS / self.pps
        self._gap = budget / len(chunks)  # fractional, so a piece takes exactly `budget` frames
        self._chunks = deque(chunks)
        self._wait = self._gap
        self._start = player.piece
        self._first = True
        self._player = player
        self._for = player.pieces_locked

    def actions(self, player: Player) -> list[Action]:
        """Call once per frame; returns the actions to apply this frame."""
        if not player.alive:
            return []
        if self._player is not player or self._for != player.pieces_locked:
            self._plan(player)
        if not self._chunks:
            return []
        self._wait -= 1
        if self._wait > 1e-9:
            return []
        if self._first and player.piece != self._start:
            self._plan(player)  # gravity moved the piece while waiting: replan from here
            self._wait = 0.0
        self._first = False
        self._wait += self._gap
        return self._chunks.popleft()
