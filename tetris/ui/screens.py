"""Screen flow (menu / battle / pause / round end / match over). No pygame: pure state machine."""
from enum import Enum, auto

from tetris.engine.match import Match
from tetris.settings import Settings


class State(Enum):
    MENU = auto()
    BATTLE = auto()
    PAUSED = auto()
    ROUND_END = auto()
    MATCH_OVER = auto()


class Flow:
    def __init__(self, settings: Settings, seed: int = 0):
        self.settings = settings
        self._seed = seed
        self.state = State.MENU
        self.match: Match | None = None
        self.quit = False

    def _new_match(self) -> None:
        self._seed += 1
        self.match = Match(self._seed, best_of=self.settings.best_of)
        self.state = State.BATTLE

    def on_key(self, name: str) -> None:
        s = self.state
        if s is State.MENU:
            if name == "enter":
                self._new_match()
            elif name == "escape":
                self.quit = True
        elif s is State.BATTLE:
            if name == "escape":
                self.state = State.PAUSED
        elif s is State.PAUSED:
            if name == "escape":
                self.state = State.BATTLE
            elif name == "q":
                self.state = State.MENU
        elif s is State.ROUND_END:
            if name == "enter":
                self.match.next_round()
                self.state = State.BATTLE
        elif s is State.MATCH_OVER:
            if name == "enter":
                self._new_match()
            elif name == "escape":
                self.state = State.MENU

    def update(self) -> None:
        """Call after each simulation tick."""
        if self.state is State.BATTLE and self.match.round_over:
            self.state = State.MATCH_OVER if self.match.match_winner is not None else State.ROUND_END
