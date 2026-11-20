import ast
import json
from pathlib import Path

from tetris.engine.board import HEIGHT, VISIBLE, WIDTH
from tetris.engine.pieces import KINDS
from tetris.input import Handling
from tetris.settings import Settings, load_settings
from tetris.ui.screens import State
from tetris.web_app import TICK, WebSession


def _make_session(seed: int = 1, keys=None) -> WebSession:
    settings = load_settings(Path("__nonexistent_settings__.json"))
    if keys is not None:
        settings = Settings(Handling(), keys, bot_pps=settings.bot_pps, best_of=settings.best_of)
    return WebSession(settings=settings, seed=seed)


def test_web_app_does_not_import_pygame_or_render():
    src = Path("tetris/web_app.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "pygame" not in imported
    assert "tetris.ui.render" not in imported


def test_web_session_lifecycle_and_snapshot_shape():
    session = _make_session(seed=7)

    snap = session.snapshot()
    assert snap["state"] == "MENU"
    assert snap["overlay"] is None
    assert snap["players"] == []
    assert snap["wins"] == [0, 0]

    # Escape on MENU must not quit or leave MENU in browser runtime.
    session.on_key_down("escape")
    assert session.flow.state is State.MENU
    assert session.flow.quit is False

    session.on_key_down("enter")
    assert session.flow.state is State.BATTLE

    snap = json.loads(session.tick_json(TICK, "[]"))
    assert snap["state"] == "BATTLE"
    assert snap["overlay"] is None
    assert len(snap["shake"]) == 2
    assert snap["level"] >= 1
    assert snap["best_of"] == 3
    assert snap["wins"] == [0, 0]
    assert len(snap["players"]) == 2

    for p in snap["players"]:
        assert len(p["board"]) == HEIGHT - VISIBLE == 20
        assert all(len(row) == WIDTH == 10 for row in p["board"])
        assert len(p["next"]) == 5
        assert p["alive"] is True
        assert p["piece_kind"] in KINDS
        assert p["ghost_kind"] == p["piece_kind"]
        assert isinstance(p["pending"], int)
        assert isinstance(p["flash_rows"], list)
        assert isinstance(p["pulse"], float)

    # Stepping frames advances both human (gravity) and bot (places pieces).
    human_before = session.flow.match.players[0].piece
    for _ in range(90):
        session.step(TICK, ())
    assert session.flow.match.players[0].piece != human_before
    assert session.flow.match.players[1].pieces_locked >= 1

    # Escape toggles PAUSED and back to BATTLE; Q while paused returns to MENU.
    session.on_key_down("escape")
    paused_snap = session.snapshot()
    assert paused_snap["state"] == "PAUSED"
    assert paused_snap["overlay"] == ["PAUSED", "Esc: resume    Q: menu"]

    session.on_key_down("escape")
    assert session.snapshot()["state"] == "BATTLE"

    session.on_key_down("escape")
    session.on_key_down("q")
    assert session.snapshot()["state"] == "MENU"


def test_shapes_json_contains_all_tetrominoes():
    session = _make_session()
    shapes = json.loads(session.shapes_json())
    assert set(shapes.keys()) == set(KINDS)
    for kind, rotations in shapes.items():
        assert len(rotations) == 4, kind
        for cells in rotations:
            assert len(cells) == 4


def test_guide_json_reflects_session_keys():
    from tetris.engine.player import Action

    keys = {**load_settings(Path("__none__.json")).keys, Action.HOLD: ["Left Shift"]}
    session = _make_session(keys=keys)
    guide = json.loads(session.guide_json())
    assert [c["slot"] for c in guide["cluster"]] == ["up", "left", "down", "right"]
    hold_row = next(r for r in guide["rows"] if r["action"] == "HOLD")
    assert hold_row["cap"] == "LSHF"
    assert hold_row["keys"] == ["left shift"]
    assert guide["rows"][-1] == {"action": None, "keys": ["escape"], "cap": "ESC", "desc": "Pause"}


def test_held_keys_input_and_dt_clamping():
    session = _make_session(seed=3, keys={
        **load_settings(Path("__none__.json")).keys,
    })
    session.on_key_down("enter")

    # Negative dt is ignored; huge dt clamps to at most 5 ticks.
    session.step(-1.0, ())
    assert session.flow.match.frame == 0
    session.step(10.0, ())
    assert session.flow.match.frame == 5

    # Hard drop via "space" locks the human piece immediately.
    before_locked = session.flow.match.players[0].pieces_locked
    session.tick_json(TICK, json.dumps(["space"]))
    assert session.flow.match.players[0].pieces_locked == before_locked + 1

    # Hold via "c" populates hold_kind.
    session.tick_json(TICK, json.dumps(["c"]))
    assert session.snapshot()["players"][0]["hold"] in KINDS


def test_index_html_py_files_exist():
    html = Path("index.html").read_text(encoding="utf-8")
    marker = "const PY_FILES = ["
    start = html.index(marker) + len(marker)
    end = html.index("];", start)
    paths = [
        line.strip().strip(",").strip('"')
        for line in html[start:end].splitlines()
        if line.strip().startswith('"')
    ]
    assert "tetris/web_app.py" in paths
    for rel in paths:
        assert Path(rel).is_file(), f"Missing file referenced by index.html: {rel}"


def test_round_end_match_over_overlays_and_key_normalization():
    keys = {**load_settings(Path("__none__.json")).keys}
    from tetris.engine.player import Action

    keys[Action.HOLD] = ["Left Shift"]
    session = _make_session(seed=5, keys=keys)
    session.on_key_down("enter")

    session.tick_json(TICK, json.dumps(["left shift"]))
    assert session.snapshot()["players"][0]["hold"] in KINDS

    # Force human round win -> ROUND_END overlay
    session.flow.match.players[1].alive = False
    session.step(TICK, ())
    round_snap = session.snapshot()
    assert round_snap["state"] == "ROUND_END"
    assert round_snap["overlay"] == ["YOU WIN THE ROUND", "Enter: next round"]

    session.on_key_down("enter")
    assert session.snapshot()["state"] == "BATTLE"

    # Force second human round win -> MATCH_OVER overlay
    session.flow.match.players[1].alive = False
    session.step(TICK, ())
    match_snap = session.snapshot()
    assert match_snap["state"] == "MATCH_OVER"
    assert match_snap["overlay"] == ["YOU WIN THE MATCH", "Enter: rematch    Esc: menu"]
    assert match_snap["wins"] == [2, 0]

    session.on_key_down("escape")
    assert session.snapshot()["state"] == "MENU"


def test_fast_tap_survives_sub_tick_frames_and_does_not_leak_from_menu():
    session = _make_session(seed=3)

    # Keys tapped on MENU must not fire once BATTLE starts.
    session.on_key_down("c")
    session.on_key_down("space")
    session.on_key_down("enter")
    assert session.flow.state is State.BATTLE

    snap = session.step(TICK, ())
    assert snap["players"][0]["hold"] is None
    assert session.flow.match.players[0].pieces_locked == 0

    # A fast tap (empty held_keys) survives sub-TICK calls and triggers HOLD once.
    session.on_key_down("c")
    snap_sub = session.step(TICK * 0.4, ())
    assert snap_sub["players"][0]["hold"] is None

    snap_tick = session.step(TICK * 0.7, ())
    assert snap_tick["players"][0]["hold"] in KINDS

    # Same for hard drop ("space"): fires once on the tick, not on sub-tick or next tick.
    before_locked = session.flow.match.players[0].pieces_locked
    session.on_key_down("space")
    session.step(TICK * 0.4, ())
    assert session.flow.match.players[0].pieces_locked == before_locked

    session.step(TICK * 0.7, ())
    assert session.flow.match.players[0].pieces_locked == before_locked + 1

    session.step(TICK, ())
    assert session.flow.match.players[0].pieces_locked == before_locked + 1


