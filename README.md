# Tetris Battle

Competitive-style Tetris for Windows (Python + pygame-ce): one human vs one bot, best-of-N rounds.

- Rules: SRS rotation and wall kicks, 7-bag, hold, ghost, 5-piece queue, 30-frame lock delay (15 resets),
  T-spins, combos, back-to-back, garbage cancelling, perfect clears.
- Battle gravity starts at level 1 and speeds up every 30 s (cap: level 15).

## Run

```bash
pip install -r requirements.txt
python -m tetris.main
```

## Controls (defaults)

| Key | Action |
|-----|--------|
| Left / Right | Move (DAS 10f, ARR 2f) |
| Down | Soft drop (SDF 20x) |
| Space | Hard drop |
| Up or X | Rotate clockwise |
| Z | Rotate counter-clockwise |
| C | Hold |
| Esc | Pause / resume / back |
| Enter | Menu and round/match confirmations |

## Settings

Optional `settings.json` next to where you run the game (hand-edited, read at startup; missing file = defaults).
Key names are pygame key names (`left`, `space`, `up`, `x`, `z`, `c`, ...).

```json
{
  "das": 10,
  "arr": 2,
  "sdf": 20,
  "bot_pps": 2.5,
  "best_of": 3,
  "keys": { "hold": ["c", "left shift"], "cw": ["up", "x"] }
}
```

A malformed file or an unknown setting/action name stops the game with a message naming the problem.

## Tests

```bash
python -m pytest
```

Design: `docs/superpowers/specs/2026-10-10-tetris-battle-design.md`; diagrams: `docs/tetris-architecture.html`, `docs/tetris-flow.html`.
