"""Hand-edited settings.json: handling values, key bindings, bot pace, match length."""
import json
from dataclasses import dataclass
from pathlib import Path

from tetris.engine.player import Action
from tetris.input import Handling

DEFAULT_KEYS: dict[Action, list[str]] = {
    Action.LEFT: ["left"],
    Action.RIGHT: ["right"],
    Action.SOFT: ["down"],
    Action.HARD: ["space"],
    Action.CW: ["up", "x"],
    Action.CCW: ["z"],
    Action.HOLD: ["c"],
}
_KEY_LABELS = {
    "left": "<-",
    "right": "->",
    "down": "v",
    "up": "^",
    "space": "SPACE",
    "left shift": "LSHF",
    "right shift": "RSHF",
    "left ctrl": "LCTL",
    "right ctrl": "RCTL",
}
_TOP_LEVEL = {"das", "arr", "sdf", "bot_pps", "best_of", "keys"}


def format_key(name: str) -> str:
    clean = name.strip()
    return _KEY_LABELS.get(clean.lower(), clean.upper())


def guide_layout(keys: dict[Action, list[str]]) -> dict:
    def norm(action: Action) -> list[str]:
        return [k.strip().lower() for k in (keys.get(action) or DEFAULT_KEYS[action])]

    cluster_spec = (
        ("up", Action.CW),
        ("left", Action.LEFT),
        ("down", Action.SOFT),
        ("right", Action.RIGHT),
    )
    cluster = []
    for slot, action in cluster_spec:
        bound = norm(action)
        cluster.append({"slot": slot, "action": action.name, "keys": bound, "label": format_key(bound[0])})

    ccw = norm(Action.CCW)
    cw = norm(Action.CW)
    hold = norm(Action.HOLD)
    hard = norm(Action.HARD)
    rows = [
        {"action": Action.CCW.name, "keys": ccw, "cap": format_key(ccw[0]), "desc": "Rotate CCW"},
        {"action": Action.CW.name, "keys": cw, "cap": "/".join(format_key(k) for k in cw), "desc": "Rotate CW"},
        {"action": Action.HOLD.name, "keys": hold, "cap": format_key(hold[0]), "desc": "Hold"},
        {"action": Action.HARD.name, "keys": hard, "cap": format_key(hard[0]), "desc": "Hard drop"},
        {"action": None, "keys": ["escape"], "cap": "ESC", "desc": "Pause"},
    ]
    return {"cluster": cluster, "rows": rows}


@dataclass
class Settings:
    handling: Handling
    keys: dict[Action, list[str]]
    bot_pps: float = 2.5
    best_of: int = 3


def _number(data: dict, name: str, default, *, integer: bool, minimum: float, strict: bool = False):
    v = data.get(name, default)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or (integer and int(v) != v):
        raise ValueError(f"settings: {name!r} must be a number, got {v!r}")
    ok = v > minimum if strict else v >= minimum
    if not ok:
        raise ValueError(f"settings: {name!r} must be {'>' if strict else '>='} {minimum}, got {v!r}")
    return int(v) if integer else float(v)


def load_settings(path: Path | str = "settings.json") -> Settings:
    path = Path(path)
    keys = {a: list(k) for a, k in DEFAULT_KEYS.items()}
    data: dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}: invalid JSON ({e})") from e
        if not isinstance(data, dict):
            raise ValueError(f"{path}: top level must be an object")
    unknown = set(data) - _TOP_LEVEL
    if unknown:
        raise ValueError(f"{path}: unknown setting {sorted(unknown)[0]!r}")
    names = {a.name.lower(): a for a in Action}
    for name, bound in data.get("keys", {}).items():
        if name not in names:
            raise ValueError(f"{path}: unknown action {name!r} in keys")
        if isinstance(bound, str):
            bound = [bound]
        if not isinstance(bound, list) or not bound or not all(isinstance(k, str) for k in bound):
            raise ValueError(f"{path}: keys.{name} must be a non-empty list of key names")
        keys[names[name]] = bound
    best_of = _number(data, "best_of", 3, integer=True, minimum=1)
    if best_of % 2 == 0:
        raise ValueError(f"settings: 'best_of' must be odd and positive, got {best_of}")
    handling = Handling(
        das=_number(data, "das", 10, integer=True, minimum=0),
        arr=_number(data, "arr", 2, integer=True, minimum=0),
        sdf=_number(data, "sdf", 20.0, integer=False, minimum=0, strict=True),
    )
    bot_pps = _number(data, "bot_pps", 2.5, integer=False, minimum=0, strict=True)
    return Settings(handling, keys, bot_pps, best_of)
