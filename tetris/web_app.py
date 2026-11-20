"""Browser runtime adapter for Tetris Battle (Pyodide + Canvas, no pygame)."""
import json
import time
from collections.abc import Callable, Iterable

from tetris.bot.bot import Bot
from tetris.engine.board import HEIGHT, VISIBLE, WIDTH
from tetris.engine.pieces import SHAPES
from tetris.engine.player import Action, Player
from tetris.input import InputHandler
from tetris.settings import DEFAULT_KEYS, Settings, guide_layout, load_settings
from tetris.ui.effects import Effects
from tetris.ui.screens import Flow, State

TICK = 1 / 60
_FLOW_KEYS = frozenset({"enter", "escape", "q"})


def _normalize_keymap(keys: dict[Action, list[str]]) -> dict[Action, list[str]]:
    source = keys or DEFAULT_KEYS
    return {action: [k.strip().lower() for k in names] for action, names in source.items()}


def _overlay(flow: Flow) -> list[str] | None:
    m = flow.match
    if flow.state is State.PAUSED:
        return ["PAUSED", "Esc: resume    Q: menu"]
    if flow.state is State.ROUND_END and m is not None:
        title = {None: "DRAW - ROUND REPLAYS", 0: "YOU WIN THE ROUND", 1: "BOT WINS THE ROUND"}[m.round_winner]
        return [title, "Enter: next round"]
    if flow.state is State.MATCH_OVER and m is not None:
        title = "YOU WIN THE MATCH" if m.match_winner == 0 else "BOT WINS THE MATCH"
        return [title, "Enter: rematch    Esc: menu"]
    return None


def _player_snapshot(player: Player, flash_rows: list[int], pulse: float) -> dict:
    ghost = player.ghost() if player.alive else None
    piece = player.piece
    return {
        "board": [row[:WIDTH] for row in player.board.cells[VISIBLE:HEIGHT]],
        "ghost": [[x, y - VISIBLE] for x, y in ghost.cells() if y >= VISIBLE] if ghost is not None else [],
        "ghost_kind": ghost.kind if ghost is not None else None,
        "piece": [[x, y - VISIBLE] for x, y in piece.cells() if y >= VISIBLE - 1] if piece is not None else [],
        "piece_kind": piece.kind if piece is not None else None,
        "hold": player.hold_kind,
        "next": player.next_kinds(5),
        "pending": sum(b.lines for b in player.pending),
        "alive": player.alive,
        "flash_rows": [r - VISIBLE for r in flash_rows if VISIBLE <= r < HEIGHT],
        "pulse": pulse,
    }


class WebSession:
    def __init__(
        self,
        settings: Settings | None = None,
        seed: int | None = None,
        opponent: Callable[[Player], list[Action]] | None = None,
    ):
        self.settings = settings or load_settings()
        self.keymap = _normalize_keymap(self.settings.keys)
        self.handler = InputHandler(self.settings.handling)
        self.flow = Flow(self.settings, seed=int(time.time()) if seed is None else seed)
        self.effects = Effects(seed=1)
        self._opponent = opponent or Bot(pps=self.settings.bot_pps).actions
        self._acc = 0.0
        self._pending_presses: set[str] = set()

    def on_key_down(self, key: str) -> None:
        name = key.strip().lower()
        if self.flow.state is State.MENU and name == "escape":
            return
        if name in _FLOW_KEYS:
            was_battle = self.flow.state is State.BATTLE
            self.flow.on_key(name)
            self.flow.quit = False
            if was_battle != (self.flow.state is State.BATTLE):
                self.handler.reset()
                self._pending_presses.clear()
            return
        if self.flow.state is State.BATTLE:
            self._pending_presses.add(name)

    def step(self, dt_sec: float, held_keys: Iterable[str] = ()) -> dict:
        dt = min(max(float(dt_sec), 0.0), 5 * TICK)
        self._acc = min(self._acc + dt, 5 * TICK)
        pressed = {k.strip().lower() for k in held_keys}
        while self._acc >= TICK:
            self._acc -= TICK
            if self.flow.state is State.BATTLE:
                tick_pressed = pressed | self._pending_presses
                self._pending_presses.clear()
                held = {action for action, names in self.keymap.items() if any(n in tick_pressed for n in names)}
                match = self.flow.match
                human = self.handler.update(held, match.players[0].gravity_frames)
                match.step(human, self._opponent(match.players[1]))
                self.effects.on_locks(match.last_locks)
                self.effects.on_pending(tuple(sum(b.lines for b in p.pending) for p in match.players))
                self.flow.update()
                if self.flow.state is not State.BATTLE:
                    self.handler.reset()
                    self._pending_presses.clear()
            else:
                self._pending_presses.clear()
            self.effects.update()
        return self.snapshot()

    def tick_json(self, dt_sec: float, held_keys_json: str = "[]") -> str:
        held_keys = json.loads(held_keys_json) if held_keys_json else ()
        return json.dumps(self.step(dt_sec, held_keys))

    def snapshot(self) -> dict:
        match = self.flow.match
        players = (
            [_player_snapshot(p, self.effects.flash_rows(i), self.effects.meter_pulse(i)) for i, p in enumerate(match.players)]
            if match is not None
            else []
        )
        return {
            "state": self.flow.state.name,
            "overlay": _overlay(self.flow),
            "shake": list(self.effects.shake_offset()),
            "level": match.level if match is not None else 1,
            "best_of": match.best_of if match is not None else self.settings.best_of,
            "wins": list(match.wins) if match is not None else [0, 0],
            "players": players,
        }

    def shapes_json(self) -> str:
        return json.dumps(SHAPES)

    def guide_json(self) -> str:
        return json.dumps(guide_layout(self.settings.keys))
