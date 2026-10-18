import pytest

from tetris.settings import load_settings
from tetris.ui.screens import Flow, State


@pytest.fixture
def flow(tmp_path):
    return Flow(load_settings(tmp_path / "none.json"), seed=1)


def finish_round(f, winner=0):
    f.match.players[1 - winner].alive = False
    f.match.step([], [])
    f.update()


def test_starts_in_menu(flow):
    assert flow.state is State.MENU and flow.match is None


def test_menu_enter_starts_battle(flow):
    flow.on_key("enter")
    assert flow.state is State.BATTLE and flow.match is not None


def test_menu_escape_quits(flow):
    flow.on_key("escape")
    assert flow.quit is True


def test_battle_escape_pauses_and_resumes_not_quits(flow):
    flow.on_key("enter")
    flow.on_key("escape")
    assert flow.state is State.PAUSED and flow.quit is False
    flow.on_key("escape")
    assert flow.state is State.BATTLE


def test_pause_q_returns_to_menu(flow):
    flow.on_key("enter")
    flow.on_key("escape")
    flow.on_key("q")
    assert flow.state is State.MENU


def test_round_end_then_next_round(flow):
    flow.on_key("enter")
    finish_round(flow)
    assert flow.state is State.ROUND_END
    flow.on_key("enter")
    assert flow.state is State.BATTLE and flow.match.round_over is False
    assert flow.match.wins == [1, 0]


def test_match_over_then_rematch_resets_wins(flow):
    flow.on_key("enter")
    finish_round(flow)
    flow.on_key("enter")
    finish_round(flow)
    assert flow.state is State.MATCH_OVER and flow.match.match_winner == 0
    flow.on_key("enter")
    assert flow.state is State.BATTLE and flow.match.wins == [0, 0] and flow.match.match_winner is None


def test_match_over_escape_returns_to_menu(flow):
    flow.on_key("enter")
    finish_round(flow)
    flow.on_key("enter")
    finish_round(flow)
    flow.on_key("escape")
    assert flow.state is State.MENU


def test_q_is_ignored_outside_pause(flow):
    flow.on_key("q")  # q only means something while paused
    assert flow.state is State.MENU
