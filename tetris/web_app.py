"""Browser runtime adapter for Tetris Battle (Pyodide + Canvas, no pygame)."""
import json
from collections.abc import Callable, Iterable

from tetris.engine.board import HEIGHT, VISIBLE, WIDTH
from tetris.engine.pieces import SHAPES
from tetris.engine.player import Action, Player
from tetris.session import TICK, GameSession
from tetris.settings import DEFAULT_KEYS, Settings, guide_layout
from tetris.ui.screens import State

_FLOW_KEYS = frozenset({"enter", "escape", "q"})


def _normalize_keymap(keys: dict[Action, list[str]]) -> dict[Action, list[str]]:
    source = keys or DEFAULT_KEYS
    return {action: [k.strip().lower() for k in names] for action, names in source.items()}


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
        self.session = GameSession(settings=settings, seed=seed, opponent=opponent)
        self.settings = self.session.settings
        self.flow = self.session.flow
        self.keymap = _normalize_keymap(self.settings.keys)
        self._pending_presses: set[str] = set()

    def on_key_down(self, key: str) -> None:
        name = key.strip().lower()
        if self.flow.state is State.MENU and name == "escape":
            return
        if name in _FLOW_KEYS:
            if self.session.on_flow_key(name):
                self._pending_presses.clear()
            self.flow.quit = False
            return
        if self.flow.state is State.BATTLE:
            self._pending_presses.add(name)

    def step(self, dt_sec: float, held_keys: Iterable[str] = ()) -> dict:
        pressed = {k.strip().lower() for k in held_keys}

        def held_for_tick() -> set[Action]:
            tick_pressed = pressed | self._pending_presses
            self._pending_presses.clear()
            return {action for action, names in self.keymap.items() if any(n in tick_pressed for n in names)}

        self.session.step(dt_sec, held_for_tick)
        if self.flow.state is not State.BATTLE:
            self._pending_presses.clear()
        return self.snapshot()

    def tick_json(self, dt_sec: float, held_keys_json: str = "[]") -> str:
        held_keys = json.loads(held_keys_json) if held_keys_json else ()
        return json.dumps(self.step(dt_sec, held_keys))

    def snapshot(self) -> dict:
        match = self.flow.match
        effects = self.session.effects
        overlay = self.flow.overlay()
        players = (
            [_player_snapshot(p, effects.flash_rows(i), effects.meter_pulse(i)) for i, p in enumerate(match.players)]
            if match is not None
            else []
        )
        return {
            "state": self.flow.state.name,
            "overlay": list(overlay) if overlay is not None else None,
            "shake": list(effects.shake_offset()),
            "level": match.level if match is not None else 1,
            "best_of": match.best_of if match is not None else self.settings.best_of,
            "wins": list(match.wins) if match is not None else [0, 0],
            "players": players,
        }

    def shapes_json(self) -> str:
        return json.dumps(SHAPES)

    def guide_json(self) -> str:
        return json.dumps(guide_layout(self.settings.keys))
