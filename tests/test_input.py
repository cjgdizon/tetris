from tetris.engine.player import Action
from tetris.input import Handling, InputHandler

L, R = Action.LEFT, Action.RIGHT


def run(handler, frames, gravity=60.0):
    """frames: list of held-sets; returns the emitted action list per frame."""
    return [handler.update(set(f), gravity) for f in frames]


def test_tap_emits_once():
    out = run(InputHandler(Handling()), [{L}, set(), set()])
    assert out == [[L], [], []]


def test_das_then_arr_schedule():
    out = run(InputHandler(Handling(das=10, arr=2)), [{L}] * 16)
    assert [i for i, o in enumerate(out) if o] == [0, 10, 12, 14]


def test_arr_zero_slides_instantly():
    out = run(InputHandler(Handling(das=10, arr=0)), [{L}] * 11)
    assert out[10] == [L] * 10 and out[9] == []


def test_never_both_directions_in_one_frame():
    out = run(InputHandler(Handling()), [{L}] * 5 + [{L, R}] * 30)
    assert out[5] == [R]
    assert all(not (L in o and R in o) for o in out)
    assert all(L not in o for o in out[5:])


def test_release_other_direction_resumes_first():
    h = InputHandler(Handling(das=10, arr=2))
    out = run(h, [{L}] * 12 + [{L, R}] * 3 + [{L}] * 4)
    assert R in out[12]
    assert any(L in o for o in out[15:])  # LEFT resumes without a fresh DAS wait


def test_release_mid_das_then_repress_moves_immediately():
    out = run(InputHandler(Handling()), [{L}] * 5 + [set()] + [{L}])
    assert out[6] == [L]


def test_reset_clears_state():
    h = InputHandler(Handling())
    run(h, [{L}] * 5)
    h.reset()
    assert h.update({L}, 60.0) == [L]


def test_edge_triggered_actions():
    for a in (Action.CW, Action.CCW, Action.HARD, Action.HOLD):
        out = run(InputHandler(Handling()), [{a}] * 5)
        assert out == [[a], [], [], [], []]


def test_soft_cadence():
    out = run(InputHandler(Handling(sdf=20.0)), [{Action.SOFT}] * 7, gravity=60.0)
    assert [i for i, o in enumerate(out) if o] == [0, 3, 6]


def test_hard_is_last_in_a_frame():
    out = InputHandler(Handling()).update({Action.HARD, Action.CW, L}, 60.0)
    assert out[-1] is Action.HARD and set(out) == {Action.HARD, Action.CW, L}
