"""Shared 60 Hz game session (no pygame) used by desktop and browser runtimes."""
import time
from collections.abc import Callable, Collection

from tetris.bot.bot import Bot
from tetris.engine.player import Action, Player
from tetris.input import InputHandler
from tetris.settings import Settings, load_settings
from tetris.ui.effects import Effects
from tetris.ui.screens import Flow, State

TICK = 1 / 60


class GameSession:
    def __init__(
        self,
        settings: Settings | None = None,
        seed: int | None = None,
        opponent: Callable[[Player], list[Action]] | None = None,
    ):
        self.settings = settings or load_settings()
        self.handler = InputHandler(self.settings.handling)
        self.flow = Flow(self.settings, seed=int(time.time()) if seed is None else seed)
        self.effects = Effects(seed=1)
        self.opponent = opponent or Bot(pps=self.settings.bot_pps).actions
        self._acc = 0.0

    def on_flow_key(self, name: str) -> bool:
        was_battle = self.flow.state is State.BATTLE
        self.flow.on_key(name)
        changed = was_battle != (self.flow.state is State.BATTLE)
        if changed:
            self.handler.reset()
        return changed

    def step(
        self,
        dt_sec: float,
        held: Collection[Action] | Callable[[], Collection[Action]] = (),
        max_ticks: int | None = None,
    ) -> int:
        dt = min(max(float(dt_sec), 0.0), 5 * TICK)
        self._acc = min(self._acc + dt, 5 * TICK)
        ticks = 0
        while self._acc >= TICK and (max_ticks is None or ticks < max_ticks):
            self._acc -= TICK
            ticks += 1
            if self.flow.state is State.BATTLE and self.flow.match is not None:
                match = self.flow.match
                tick_held = held() if callable(held) else held
                human = self.handler.update(tick_held, match.players[0].gravity_frames)
                match.step(human, self.opponent(match.players[1]))
                self.effects.on_locks(match.last_locks)
                self.effects.on_pending(tuple(sum(b.lines for b in p.pending) for p in match.players))
                self.flow.update()
                if self.flow.state is not State.BATTLE:
                    self.handler.reset()
            self.effects.update()
        return ticks
