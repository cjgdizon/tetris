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


_STATE_TRANSITIONS = {
    (State.BATTLE, "escape"): State.PAUSED,
    (State.PAUSED, "escape"): State.BATTLE,
    (State.PAUSED, "q"): State.MENU,
    (State.MATCH_OVER, "escape"): State.MENU,
}


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
        nxt = _STATE_TRANSITIONS.get((self.state, name))
        if nxt is not None:
            self.state = nxt
        elif (self.state, name) in ((State.MENU, "enter"), (State.MATCH_OVER, "enter")):
            self._new_match()
        elif self.state is State.MENU and name == "escape":
            self.quit = True
        elif self.state is State.ROUND_END and name == "enter" and self.match is not None:
            self.match.next_round()
            self.state = State.BATTLE

    def update(self) -> None:
        """Call after each simulation tick."""
        if self.state is State.BATTLE and self.match is not None and self.match.round_over:
            self.state = State.MATCH_OVER if self.match.match_winner is not None else State.ROUND_END

    def overlay(self) -> tuple[str, str] | None:
        """Title and hint for the current overlay, or None while the battle is live."""
        m = self.match
        if m is None:
            return None
        if self.state is State.PAUSED:
            return "PAUSED", "Esc: resume    Q: menu"
        if self.state is State.ROUND_END:
            title = {None: "DRAW - ROUND REPLAYS", 0: "YOU WIN THE ROUND", 1: "BOT WINS THE ROUND"}[m.round_winner]
            return title, "Enter: next round"
        if self.state is State.MATCH_OVER:
            title = "YOU WIN THE MATCH" if m.match_winner == 0 else "BOT WINS THE MATCH"
            return title, "Enter: rematch    Esc: menu"
        return None
