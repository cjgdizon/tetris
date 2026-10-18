import json

import pytest

from tetris.engine.player import Action
from tetris.settings import load_settings


def write(tmp_path, text):
    p = tmp_path / "settings.json"
    p.write_text(text)
    return p


def test_missing_file_gives_defaults(tmp_path):
    s = load_settings(tmp_path / "nope.json")
    assert (s.handling.das, s.handling.arr, s.handling.sdf) == (10, 2, 20.0)
    assert (s.bot_pps, s.best_of) == (2.5, 3)
    assert s.keys[Action.CCW] == ["z"] and s.keys[Action.HOLD] == ["c"]
    assert s.keys[Action.CW] == ["up", "x"] and s.keys[Action.HARD] == ["space"]


def test_override_values(tmp_path):
    s = load_settings(write(tmp_path, json.dumps({"das": 6, "arr": 0, "sdf": 40, "bot_pps": 3, "best_of": 5})))
    assert (s.handling.das, s.handling.arr, s.handling.sdf, s.bot_pps, s.best_of) == (6, 0, 40.0, 3.0, 5)


def test_partial_keys_merge(tmp_path):
    s = load_settings(write(tmp_path, '{"keys": {"hold": ["shift", "c"]}}'))
    assert s.keys[Action.HOLD] == ["shift", "c"] and s.keys[Action.LEFT] == ["left"]


def test_malformed_json_raises_value_error_mentioning_path(tmp_path):
    p = write(tmp_path, "{not json")
    with pytest.raises(ValueError) as e:
        load_settings(p)
    assert "settings.json" in str(e.value)


def test_unknown_action_name_raises_value_error_naming_it(tmp_path):
    with pytest.raises(ValueError, match="teleport"):
        load_settings(write(tmp_path, '{"keys": {"teleport": ["t"]}}'))


def test_unknown_top_level_key_raises(tmp_path):
    with pytest.raises(ValueError, match="gravity"):
        load_settings(write(tmp_path, '{"gravity": 3}'))


@pytest.mark.parametrize("body", ['{"das": -1}', '{"arr": -2}', '{"sdf": 0}', '{"bot_pps": 0}', '{"das": "x"}'])
def test_bad_numbers_raise(tmp_path, body):
    with pytest.raises(ValueError):
        load_settings(write(tmp_path, body))


@pytest.mark.parametrize("n", [0, 2, -3])
def test_best_of_must_be_odd_positive(tmp_path, n):
    with pytest.raises(ValueError, match="best_of"):
        load_settings(write(tmp_path, json.dumps({"best_of": n})))
