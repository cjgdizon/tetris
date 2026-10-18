# Tetris Battle (Windows, Python + pygame) — Design

## Context
Build a competitive-grade Tetris for Windows in an empty folder (`C:\Users\Cj\Documents\Tetris`). Focus is **battle mode: player vs one strong bot only**. Chosen via brainstorming: headless engine + thin pygame shell, modern competitive attack rules, keyboard only with standard controls, best-of-N matches, visual effects.

**Out of v1:** player vs player, solo modes (Marathon/Sprint/Ultra), sound, gamepad, bot difficulty levels, online play, in-game key-rebind screen, saving settings from the UI.

**Assumptions (flagged, easy to change):**
- Settings (keys, DAS/ARR/SDF) live in a hand-edited `settings.json` read at startup. No save-from-UI.
- Bot plays at a human-like pace (default ~2.5 pieces/sec, one constant) so a good player can beat it.
- Battle gravity starts at level 1 and speeds up on a timer (every 30s, capped) so matches end.

## Architecture
Pure-Python engine with **no pygame import**. pygame only draws and reads keys. The bot drives the same engine API as a human.

```
tetris/
  engine/
    pieces.py   # 7 tetrominoes, rotation states, SRS kick tables (JLSTZ, I; O none)
    board.py    # 10x40 grid (20 visible), collision, lock, line clear, garbage insert
    bag.py      # seedable 7-bag, next-queue
    attack.py   # attack table, combo/B2B, cancel, garbage hole selection
    player.py   # one player's state + step(actions, frame): gravity, lock delay, hold, T-spin, scoring
    match.py    # two Players (human + bot), garbage routing, rounds, best-of-N
  bot/
    placements.py  # BFS of reachable final placements (incl. kicks, tucks, spins)
    evaluate.py    # weighted board heuristic + attack/T-slot bonus
    bot.py         # picks placement (current + hold + 2 next), emits timed actions at target PPS
  ui/
    render.py   # boards, hold, next, garbage meter, HUD (drawn with primitives, no art assets)
    effects.py  # line-clear flash, screen shake on big attacks, meter pulse
    screens.py  # menu (Play vs Bot / Quit), battle, pause, match-over + rematch
  input.py      # keymap -> actions, DAS/ARR/SDF handling (frame-based)
  settings.py   # defaults + load settings.json
  main.py       # fixed 60 Hz timestep loop
tests/
requirements.txt  # pygame-ce, pytest
```

## Engine rules
- **Timing:** fixed 60 Hz tick; all timings in frames. Engine is deterministic given a seed.
- **Actions:** LEFT, RIGHT, SOFT, HARD, CW, CCW, HOLD. Human input (DAS/ARR) and bot both produce these.
- **Core:** 7-bag, hold (once per piece), ghost, 5-piece next queue, SRS with wall kicks, lock delay 30f with 15-move reset cap.
- **T-spin:** 3-corner rule with mini detection, only if last successful move was a rotation.
- **Attack (modern):** single 0, double 1, triple 2, Tetris 4; T-spin single 2 / double 4 / triple 6, mini 0; perfect clear 10; back-to-back +1; combo table [0,0,1,1,1,2,2,3,3,4,4,4,5]. All values in one table so they can be rebalanced.
- **Garbage:** attack cancels own pending garbage first; remainder queues for the opponent. Pending garbage lands after a lock with no line clear, max 8 lines per lock. One shared hole column per attack batch, new random column per batch.
- **Top-out:** block-out (spawn overlap), lock-out above the visible area, or garbage push-out ends the round; match = best-of-N (default 3).

## Bot
Enumerate every reachable final placement for current piece and hold (BFS over move/rotate/drop, so tucks and T-spins are legal), score each resulting board, search 2 pieces ahead with a small beam. Heuristic: height, holes, bumpiness, wells, row transitions, plus bonuses for T-slots, combo/B2B continuation, and an attack-aware term. Pace controller releases the chosen move as timed actions at the target PPS.

## Controls (defaults, editable in `settings.json`)
Standard guideline layout, single human player:
- Left/Right arrows move, Down arrow soft drop, Space hard drop.
- Up arrow rotate clockwise (X also), Z rotate counter-clockwise, C hold.
- Esc pause/back.
- DAS 10f, ARR 2f, SDF 20x.

## Rendering / effects
1280x720 window, two boards side by side, hold on the left and next queue on the right of each board, vertical garbage meter beside each board. Line-clear flash, screen shake when an attack is 4+ lines, meter pulse on incoming garbage.

## Build order
1. Engine core (pieces, board, bag, SRS, line clear) + tests.
2. Player logic (gravity, lock delay, hold, T-spin, scoring) + a minimal single-board pygame shell to feel it.
3. Battle: attack table, cancel, garbage, two boards, match/best-of-N (bot stubbed with random placements at first).
4. Bot (placements, evaluator, pace controller) + bot-vs-bot headless test.
5. Menu, match-over screen, effects, polish.

## Verification
- `pytest`: SRS kick cases, line clears, T-spin / mini detection on known setups, attack table and combo/B2B, garbage cancel and hole column, 7-bag property, determinism by seed.
- Bot checks: every emitted placement is legal; a headless bot-vs-bot match runs to completion without error for several seeds.
- Manual: run `python -m tetris.main`; verify DAS/ARR feel, the standard key layout, vs-bot match end to end including best-of-3 and rematch.
