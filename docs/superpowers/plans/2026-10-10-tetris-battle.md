# Tetris Battle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Windows desktop Tetris where one human plays best-of-N battles against one strong bot, using modern competitive rules (SRS, T-spins, combos, back-to-back, garbage cancelling).

**Architecture:** A pure-Python engine (`tetris/engine`, no pygame import) holds all rules and is driven by `Action` lists per 60 Hz frame. Human input (`input.py`) and the bot (`tetris/bot`) both produce those same actions. pygame (`tetris/ui`, `main.py`) only draws and reads keys.

**Tech Stack:** Python 3.10+ (uses `X | None`), pygame-ce, pytest.

**Spec:** `docs/superpowers/specs/2026-10-10-tetris-battle-design.md` (diagrams: `docs/tetris-architecture.html`, `docs/tetris-flow.html`)

## Global Constraints

- Engine (`tetris/engine`, `tetris/bot`) must never import pygame. Only `tetris/ui/*`, `tetris/main.py` may.
- Fixed 60 Hz timestep; all engine timings are in frames; engine is deterministic for a given seed.
- Board 10 wide x 40 tall, 20 visible. Coordinates are `(x, y)` with **y down**: rows 0-19 hidden, rows 20-39 visible, floor is row 39.
- Lock delay 30 frames, capped at 15 move/rotate resets. Pending garbage lands only after a lock with no line clear, max 8 lines per lock, one hole column per attack batch.
- Attack table: single 0, double 1, triple 2, Tetris 4; T-spin single 2 / double 4 / triple 6; T-spin mini 0; perfect clear 10; back-to-back +1; combo table `[0,0,1,1,1,2,2,3,3,4,4,4,5]`.
- Defaults: DAS 10f, ARR 2f, SDF 20x, bot ~2.5 pieces/sec, best-of 3. Battle gravity starts at level 1, +1 level every 30 s, capped at 15.
- Controls (defaults, from `settings.json`): Left/Right move, Down soft drop, Space hard drop, Up and X rotate CW, Z rotate CCW, C hold, Esc pause/back.
- Window 1280x720, drawn with primitives only (no art assets). No sound, no gamepad, no PvP, no solo modes, no in-game rebinding.
- Git: the repo root is `C:\Users\Cj\Documents` and has many unrelated pending deletions. Every commit step stages **only the files named in that task** (`git add <paths>`), never `git add -A` or `.`.

## Review Focus

1. Both players top out in the same frame: no round winner, round replays, win counts unchanged (Task 7).
2. `settings.json` missing, malformed, or with an unknown key or bad value: defaults on missing, a clear `ValueError` otherwise (Task 8).
3. Left and Right held together, or a key released mid-DAS, or pause/resume: never emits both directions in one frame; `reset()` clears held state (Task 8).
4. Rotating near the ceiling or walls where a kick would leave the board: never returns an out-of-bounds or colliding piece (Task 3).
5. Bot given a board with no legal placement: returns a fallback and never raises (Task 11).

---

## File Structure

```
requirements.txt  pytest.ini  .gitignore  README.md
settings.json                      # optional, hand-edited, read at startup
tetris/__init__.py
tetris/main.py                     # 60 Hz loop, key polling, wiring
tetris/input.py                    # Handling, InputHandler (DAS/ARR/SDF)
tetris/settings.py                 # Settings, load_settings
tetris/engine/__init__.py
tetris/engine/pieces.py            # shapes, spawn, SRS kick data, Piece
tetris/engine/board.py             # grid, collision, clears, garbage, rotation
tetris/engine/tspin.py             # tspin_kind (added to the spec's file list)
tetris/engine/bag.py               # seedable 7-bag
tetris/engine/attack.py            # attack table, Batch, cancel, land
tetris/engine/player.py            # Action, LockResult, Player
tetris/engine/match.py             # Match: two players, garbage routing, rounds
tetris/bot/__init__.py
tetris/bot/placements.py           # BFS reachable placements
tetris/bot/evaluate.py             # Weights, evaluate
tetris/bot/bot.py                  # Bot: search + pace controller
tetris/ui/__init__.py
tetris/ui/render.py  effects.py  screens.py
tests/                             # one test_*.py per module above
```

---

### Task 1: Scaffold and pieces

**Files:**
- Create: `requirements.txt` (`pygame-ce`, `pytest`), `pytest.ini` (`[pytest]` / `testpaths = tests`), `.gitignore` (`__pycache__/`, `.pytest_cache/`, `*.pyc`, `.venv/`), `tetris/__init__.py`, `tetris/engine/__init__.py`, `tetris/engine/pieces.py`, `tests/test_pieces.py`

**Interfaces:**
- Produces (`tetris/engine/pieces.py`):
  - `KINDS = "IOTSZJL"`
  - `SHAPES: dict[str, list[list[tuple[int,int]]]]` kind -> 4 rotation states (0=spawn, 1=R, 2=180, 3=L) -> 4 `(x, y)` cells inside the SRS box (4x4 for I and O, 3x3 otherwise), y down
  - `SPAWN = (3, 18)` box origin for every kind
  - `KICKS: dict[str, dict[tuple[int,int], list[tuple[int,int]]]]` keys `"JLSTZ"` and `"I"` (and `"O"`: only `[(0,0)]`), inner key `(from_rot, to_rot)`, value = 5 `(dx, dy)` offsets **in y-down coordinates** (negate the y of the Tetris-guideline SRS tables, which are y-up)
  - `@dataclass(frozen=True) class Piece: kind: str; x: int; y: int; rot: int = 0` with `cells() -> list[tuple[int,int]]` (absolute), `moved(dx, dy) -> Piece`, `with_rot(rot, x, y) -> Piece`

- [ ] **Step 1: Write failing tests in `tests/test_pieces.py`**
  - `test_every_kind_has_four_states_of_four_cells`
  - `test_t_spawn_cells`: `sorted(Piece("T",3,18,0).cells()) == [(3,19),(4,18),(4,19),(5,19)]`
  - `test_i_spawn_cells`: `sorted(Piece("I",3,18,0).cells()) == [(3,19),(4,19),(5,19),(6,19)]`
  - `test_o_spawn_cells`: `sorted(Piece("O",3,18,0).cells()) == [(4,18),(4,19),(5,18),(5,19)]`
  - `test_states_are_distinct_except_o`: T, S, Z, J, L, I have 4 distinct cell sets across states; O's four states are identical
  - `test_kick_tables_pinned` (y-down values): `KICKS["JLSTZ"][(0,1)] == [(0,0),(-1,0),(-1,-1),(0,2),(-1,2)]`, `KICKS["JLSTZ"][(3,0)] == [(0,0),(-1,0),(-1,1),(0,-2),(-1,-2)]`, `KICKS["I"][(0,1)] == [(0,0),(-2,0),(1,0),(-2,1),(1,-2)]`
- [ ] **Step 2:** `pytest tests/test_pieces.py -v` -> FAIL (import error)
- [ ] **Step 3: Implement `pieces.py`** with standard SRS shapes (spawn orientation has the flat side up, cells in box rows 0-1; I in box row 1) and the full standard guideline kick tables for all 8 rotation transitions of JLSTZ and I, y negated.
- [ ] **Step 4:** `pytest tests/test_pieces.py -v` -> PASS
- [ ] **Step 5: Commit**
```bash
git add requirements.txt pytest.ini .gitignore tetris/__init__.py tetris/engine/__init__.py tetris/engine/pieces.py tests/test_pieces.py
git commit -m "feat: scaffold project and SRS piece data"
```

### Task 2: Board

**Files:** Create `tetris/engine/board.py`, `tests/test_board.py`

**Interfaces:**
- Consumes: `Piece` from Task 1
- Produces (`tetris/engine/board.py`):
  - constants `WIDTH = 10`, `HEIGHT = 40`, `VISIBLE = 20`
  - `class Board` with `cells: list[list[str | None]]` indexed `[y][x]` (`"G"` = garbage, otherwise the piece kind or `"X"`)
  - `Board.from_ascii(rows: list[str]) -> Board`: rows top-to-bottom, each 10 chars, `X` filled `.` empty, bottom-aligned to row 39
  - `occupied(x: int, y: int) -> bool` (out of bounds counts as occupied, including `y < 0`)
  - `collides(piece: Piece) -> bool`
  - `drop_distance(piece: Piece) -> int` (rows until grounded)
  - `lock(piece: Piece) -> None`
  - `clear_lines() -> list[int]` (y of cleared rows before removal, ascending; rows above fall)
  - `add_garbage(lines: int, hole: int) -> bool` (shift stack up, fill bottom `lines` rows with `"G"` except column `hole`; returns True if a filled cell was pushed above row 0)
  - `is_empty() -> bool`, `copy() -> Board`, `heights() -> list[int]` (per column, 0 = empty, counted from the floor)

- [ ] **Step 1: Write failing tests**
  - `test_collides_walls_floor_ceiling`: `Piece("O",-2,18)`, `Piece("O",8,18)`, `Piece("O",3,39)`, `Piece("O",3,-1)` all collide; `Piece("O",3,18)` does not
  - `test_lock_and_clear_two_rows`: `Board.from_ascii(["XXXXXXXXXX","XXXXXXXXXX","X........."])` -> `clear_lines() == [37, 38]`, then `cells[39][0] == "X"` and `cells[38]` is all `None`
  - `test_add_garbage_shifts_up_with_hole`: from `["X........."]`, `add_garbage(2, 4)` returns False; rows 38 and 39 have `None` only at x=4 and `"G"` elsewhere; the old cell is at `(0, 37)`
  - `test_add_garbage_reports_push_out`: with `cells[0][0] = "X"`, `add_garbage(1, 0)` is True
  - `test_drop_distance`: `Piece("I",3,18,0)` on an empty board -> 20
  - `test_heights_and_is_empty_and_copy_independent`
- [ ] **Step 2:** run `pytest tests/test_board.py -v` -> FAIL
- [ ] **Step 3: Implement `board.py`** per Interfaces.
- [ ] **Step 4:** run -> PASS
- [ ] **Step 5: Commit** `git add tetris/engine/board.py tests/test_board.py` / `feat: board with collision, clears, garbage`

### Task 3: SRS rotation and T-spin classification

**Files:** Modify `tetris/engine/board.py`; Create `tetris/engine/tspin.py`, `tests/test_rotation.py`, `tests/test_tspin.py`

**Interfaces:**
- Consumes: `Board`, `Piece`, `KICKS`, `SHAPES`
- Produces:
  - `Board.try_rotate(piece: Piece, direction: int) -> tuple[Piece, int] | None` (`direction` +1 = CW, -1 = CCW; tries the 5 offsets for `(rot, new_rot)` in order, returns the first non-colliding piece and its kick index 0-4, else None)
  - `tspin_kind(board: Board, piece: Piece, rotated: bool, kick_index: int) -> str` returning `"none" | "mini" | "full"`. `piece` is the final pose, not yet locked. Rule: only kind `T`; requires `rotated`; center is `(x+1, y+1)`; count occupied diagonal corners (walls count) and require >= 3; "front" corners are the two on the side the T points to (rot 0 up, 1 right, 2 down, 3 left); both front occupied -> `full`; otherwise `full` if `kick_index == 4` else `mini`.

- [ ] **Step 1: Write failing tests**
  - `test_rotate_cw_open_field`: `Piece("T",3,18,0)` -> `(Piece("T",3,18,1), 0)`
  - `test_rotate_uses_first_free_kick`: block `(4,32)` on an otherwise empty board; `try_rotate(Piece("T",3,30,0), +1) == (Piece("T",2,30,1), 1)`
  - `test_rotate_never_returns_colliding_or_out_of_bounds` (review focus 4): for kinds in `KINDS`, x in -2..9, y in -3..3, rot 0..3, direction +-1 on an empty board, a non-None result never collides
  - Fixture A rows (bottom three, y37..39): `["...X......","X...XXXXXX","XX.XXXXXXX"]`, piece `Piece("T",1,37,2)`:
    - `test_tspin_full`: `tspin_kind(A, piece, True, 0) == "full"`
    - `test_not_rotated_is_none`: `rotated=False` -> `"none"`
    - `test_non_t_is_none`
  - Fixture B (mini): `[".X.X......","X...XXXXXX","X..XXXXXXX"]`, same piece: kick 0 -> `"mini"`, kick 4 -> `"full"`
- [ ] **Step 2:** run -> FAIL
- [ ] **Step 3: Implement** `Board.try_rotate` and `tspin.py` per Interfaces.
- [ ] **Step 4:** run -> PASS
- [ ] **Step 5: Commit** `git add tetris/engine/board.py tetris/engine/tspin.py tests/test_rotation.py tests/test_tspin.py` / `feat: SRS rotation and T-spin detection`

### Task 4: Bag and attack rules

**Files:** Create `tetris/engine/bag.py`, `tetris/engine/attack.py`, `tests/test_bag.py`, `tests/test_attack.py`

**Interfaces:**
- Produces:
  - `class Bag`: `__init__(seed: int)`, `next() -> str`, `peek(n: int) -> list[str]` (does not consume)
  - `COMBO_TABLE = [0,0,1,1,1,2,2,3,3,4,4,4,5]`
  - `@dataclass class Batch: lines: int; hole: int`
  - `is_difficult(lines: int, tspin: str) -> bool` (Tetris, or any T-spin with lines > 0)
  - `attack_lines(lines: int, tspin: str, b2b: bool, combo: int, perfect_clear: bool) -> int` (`combo` = consecutive line-clearing locks before this one, clamped to the table end; `b2b` = previous clear was difficult; returns 10 for a perfect clear; mini is base 0; +1 when `b2b` and `is_difficult`; plus `COMBO_TABLE[combo]`; returns 0 when `lines == 0`)
  - `cancel(pending: list[Batch], attack: int) -> int` (FIFO, mutates `pending`, returns attack left over)
  - `land(pending: list[Batch], limit: int = 8) -> list[Batch]` (FIFO, splits a batch at the limit, mutates `pending`, returns batches that land)

- [ ] **Step 1: Write failing tests**
  - Bag: `test_each_window_of_seven_has_all_kinds` (check 5 windows), `test_same_seed_same_sequence`, `test_peek_does_not_consume`
  - Attack: `test_base_table`: single/double/triple/tetris -> 0,1,2,4 (all `tspin="none"`, `b2b=False`, `combo=0`); full T-spin 1/2/3 lines -> 2,4,6; mini any lines -> 0
  - `test_b2b_bonus`: `attack_lines(4,"none",True,0,False) == 5`, `attack_lines(2,"full",True,0,False) == 5`, `attack_lines(2,"none",True,0,False) == 1`
  - `test_combo_table`: single with combo 2 -> 1, combo 5 -> 2, combo 99 -> 5
  - `test_perfect_clear_is_ten`, `test_no_lines_no_attack`
  - `test_cancel`: pending `[Batch(3,0),Batch(2,5)]`, attack 4 -> pending `[Batch(1,5)]`, returns 0; attack 6 -> pending `[]`, returns 1
  - `test_land_splits_at_limit`: `[Batch(6,1),Batch(5,2)]` -> returns `[Batch(6,1),Batch(2,2)]`, pending `[Batch(3,2)]`
- [ ] **Step 2:** run -> FAIL
- [ ] **Step 3: Implement** both modules (`Bag` shuffles 7 kinds with `random.Random(seed)` and refills when empty).
- [ ] **Step 4:** run -> PASS
- [ ] **Step 5: Commit** `git add tetris/engine/bag.py tetris/engine/attack.py tests/test_bag.py tests/test_attack.py` / `feat: bag and attack rules`

### Task 5: Player core (movement, gravity, lock delay, hold)

**Files:** Create `tetris/engine/player.py`, `tests/test_player_core.py`

**Interfaces:**
- Consumes: `Board`, `Piece`, `SPAWN`, `Bag`, `Batch`
- Produces (`tetris/engine/player.py`):
  - `class Action(Enum)`: `LEFT, RIGHT, SOFT, HARD, CW, CCW, HOLD` (`SOFT` = move down exactly one row per occurrence)
  - `class Player`: `__init__(seed: int, gravity_frames: float = 60.0)`
  - attributes: `board: Board`, `piece: Piece | None`, `hold_kind: str | None`, `pending: list[Batch]`, `alive: bool`, `pieces_locked: int`, `gravity_frames: float` (frames per row, mutable), `last_move_rotation: bool`, `last_kick: int`
  - `step(actions: Sequence[Action]) -> LockResult | None` (processes actions in order; stops processing after a lock; then applies gravity for the frame and the lock-delay timer; returns the `LockResult` if a piece locked this frame)
  - `next_kinds(n: int = 5) -> list[str]`, `ghost() -> Piece | None`
- `LockResult` is defined in Task 6; in this task `step` returns None and locking calls a `_lock_piece()` stub that only does `board.lock`, increments `pieces_locked` and spawns the next piece (Task 6 replaces its body).

Behavior to implement: spawn at `Piece(kind, 3, 18, 0)` (collision at spawn sets `alive = False`); LEFT/RIGHT/CW/CCW only on success; any successful move/rotate while grounded resets the 30-frame lock timer, at most 15 times per piece (counter resets when the piece reaches a new lowest row); HARD drops and locks instantly; HOLD swaps once per piece (a second HOLD before the next lock is ignored; first hold spawns the next bag piece); successful rotate sets `last_move_rotation = True` and `last_kick`; any successful move or non-zero drop sets `last_move_rotation = False`; gravity accumulates `1 / gravity_frames` rows per frame.

- [ ] **Step 1: Write failing tests**
  - `test_spawn_pose`: new `Player(1)` has `piece.x, piece.y, piece.rot == 3, 18, 0`
  - `test_left_moves_and_wall_blocks`: LEFT 3 times from spawn -> `x == 0`; a 4th does nothing
  - `test_hard_drop_locks_and_spawns`: `step([Action.HARD])`: `pieces_locked == 1`, some cell in row 39 is filled, new piece at spawn
  - `test_gravity_one_row_per_n_frames`: `gravity_frames = 2`, two `step([])` calls move `piece.y` by exactly 1
  - `test_lock_delay_30_frames`: set `gravity_frames = 1e9`, `piece = Piece("O",3,38,0)`; after 29 empty steps `pieces_locked == 0`, after 30 it is 1
  - `test_move_reset_cap`: same grounded O, alternate LEFT/RIGHT every frame for 60 frames -> `pieces_locked >= 1` (without the 15-reset cap it would never lock)
  - `test_hold_once_per_piece`: first HOLD sets `hold_kind` to the old kind and spawns the next; a second HOLD in the same turn changes nothing; after a HARD lock, HOLD works again
  - `test_ghost_equals_hard_drop_pose`
  - `test_soft_moves_exactly_one_row`
  - `test_cw_sets_last_move_rotation`
- [ ] **Step 2:** run -> FAIL
- [ ] **Step 3: Implement** per the behavior above.
- [ ] **Step 4:** run -> PASS
- [ ] **Step 5: Commit** `git add tetris/engine/player.py tests/test_player_core.py` / `feat: player movement, gravity, lock delay, hold`

### Task 6: Player lock resolution

**Files:** Modify `tetris/engine/player.py`; Create `tests/test_player_lock.py`

**Interfaces:**
- Consumes: `tspin_kind`, `attack_lines`, `is_difficult`, `cancel`, `land`
- Produces:
  - `@dataclass class LockResult: lines: int; tspin: str; sent: int; cancelled: int; perfect_clear: bool; cleared_rows: list[int]; garbage_landed: int`
  - Player attributes `combo: int` (starts 0) and `b2b: bool` (starts False). `step` now returns the `LockResult` on a lock.

Lock order: `tspin_kind` (before locking, using `last_move_rotation`/`last_kick`) -> `board.lock` -> lock-out check (every cell of the locked piece has `y < 20`, i.e. entirely above the visible field -> `alive = False`) -> `clear_lines` -> perfect-clear check (`board.is_empty()` after a clear) -> `attack_lines` using current `combo`/`b2b` -> `cancel(pending, attack)`; `sent` = leftover -> update `combo` (+1 if lines > 0 else reset to 0) and `b2b` (set True after a difficult clear, False after a non-difficult clear, unchanged when `lines == 0`) -> if `lines == 0`, `land(pending, 8)` and `board.add_garbage` for each landed batch (a True return sets `alive = False`) -> spawn next piece (collision = block-out, `alive = False`).

- [ ] **Step 1: Write failing tests** (helper `tetris_setup(player)` that sets `player.board = Board.from_ascii(["X.........", *["XXXXXXXXX."]*4])` and `player.piece = Piece("I",7,36,1)`)
  - `test_tetris_sends_four`: `step([Action.HARD])` -> `lines == 4`, `sent == 4`, `perfect_clear is False`, `cleared_rows == [36,37,38,39]`
  - `test_second_tetris_gets_b2b`: two Tetrises in a row -> second `sent == 5`
  - `test_combo_sequence`: three single clears in a row (reset the board each time with rows `["XXXXXXXXX."]` and `Piece("I",7,36,1)`) -> `sent` is `[0, 0, 1]`
  - `test_perfect_clear_ten`: board `["XXXXXXXXX."]*4` only + vertical I -> `sent == 10`
  - `test_tspin_double`: fixture A from Task 3 (`Board.from_ascii(["...X......","X...XXXXXX","XX.XXXXXXX"])`), `piece = Piece("T",1,37,2)`, `last_move_rotation = True`, `last_kick = 0`, `step([Action.HARD])` -> `lines == 2`, `tspin == "full"`, `sent == 4`
  - `test_no_clear_lands_garbage_max_eight`: `pending = [Batch(10,3)]`, a no-clear lock -> `garbage_landed == 8`, `pending == [Batch(2,3)]`, bottom 8 rows have `None` only at x=3
  - `test_clear_cancels_pending`: `pending = [Batch(3,0)]`, Tetris -> `sent == 1`, `cancelled == 3`, `pending == []`, no garbage landed
  - `test_lock_out_above_visible`: rows 20-39 filled with `"XXXXXXXXX."`, `piece = Piece("O",3,10,0)`, HARD -> `alive is False`
  - `test_block_out_on_spawn`: fill the spawn cells, lock a piece -> `alive is False`
  - `test_garbage_push_out`: nearly full board plus `pending = [Batch(8,0)]` -> `alive is False`
- [ ] **Step 2:** run -> FAIL
- [ ] **Step 3: Implement** in `player.py` per the lock order above.
- [ ] **Step 4:** run -> PASS; also re-run `pytest tests/test_player_core.py -v`
- [ ] **Step 5: Commit** `git add tetris/engine/player.py tests/test_player_lock.py` / `feat: lock resolution, attack, garbage, top-out`

### Task 7: Match

**Files:** Create `tetris/engine/match.py`, `tests/test_match.py`

**Interfaces:**
- Consumes: `Player`, `Action`, `LockResult`, `Batch`
- Produces (`tetris/engine/match.py`):
  - `class Match`: `__init__(seed: int, best_of: int = 3)`
  - attributes: `players: tuple[Player, Player]` (0 = human, 1 = bot), `wins: list[int]`, `frame: int`, `round_over: bool`, `round_winner: int | None`, `match_winner: int | None`, `last_locks: tuple[LockResult | None, LockResult | None]`
  - `step(actions0: Sequence[Action], actions1: Sequence[Action]) -> None` (no-op once `round_over`)
  - `next_round() -> None` (new boards, new seed, wins kept, `frame` reset)
  - `level` property; helper `gravity_for_level(level: int) -> float` = `60 * (0.8 - (level-1)*0.007) ** (level-1)`
- Behavior: both players share one bag seed per round (identical piece sequence); when a lock has `sent > 0`, append `Batch(sent, hole)` to the opponent's `pending` with `hole = rng.randrange(10)` from a match-level `random.Random`; level = `min(15, 1 + frame // 1800)`, applied to both players' `gravity_frames` each step; after both players have stepped, if exactly one is dead the other wins the round (`wins += 1`), if both are dead there is no winner and `wins` is unchanged; `match_winner` is set when a side reaches `best_of // 2 + 1` wins.

- [ ] **Step 1: Write failing tests**
  - `test_players_share_piece_sequence`: `players[0].next_kinds() == players[1].next_kinds()`
  - `test_tetris_routes_garbage_to_opponent`: set up a Tetris for player 0 (Task 6 helper) -> `players[1].pending` is one `Batch(4, h)` with `0 <= h < 10`
  - `test_garbage_cancelled_before_sending`: assert the sender's own pending is cancelled first (sender had `Batch(4,0)` pending, cleared a Tetris -> `players[1].pending == []`)
  - `test_level_speeds_up`: after 1800 `step([], [])` calls, `abs(players[0].gravity_frames - gravity_for_level(2)) < 1e-6` and `gravity_for_level(2) == 60 * 0.793`; after 100000 frames level is 15
  - `test_simultaneous_top_out_replays_round` (review focus 1): set both `alive = False`, `step` -> `round_over is True`, `round_winner is None`, `wins == [0, 0]`; `next_round()` -> `round_over is False`, boards empty
  - `test_best_of_three_winner`: player 1 dies twice across two rounds -> `wins == [2, 0]`, `match_winner == 0`
- [ ] **Step 2:** run -> FAIL
- [ ] **Step 3: Implement** per Behavior.
- [ ] **Step 4:** run -> PASS
- [ ] **Step 5: Commit** `git add tetris/engine/match.py tests/test_match.py` / `feat: match with garbage routing and best-of-N`

### Task 8: Input handling and settings

**Files:** Create `tetris/input.py`, `tetris/settings.py`, `tests/test_input.py`, `tests/test_settings.py`

**Interfaces:**
- Produces:
  - `@dataclass class Handling: das: int = 10; arr: int = 2; sdf: float = 20.0`
  - `class InputHandler`: `__init__(handling: Handling)`, `update(held: set[Action], gravity_frames: float) -> list[Action]` (call once per frame), `reset() -> None`
  - `@dataclass class Settings: handling: Handling; keys: dict[Action, list[str]]; bot_pps: float; best_of: int`
  - `load_settings(path: Path | str = "settings.json") -> Settings` (missing file -> defaults; keys are pygame key names, e.g. `"left"`, `"space"`; JSON shape `{"das":10,"arr":2,"sdf":20,"bot_pps":2.5,"best_of":3,"keys":{"left":["left"],...,"hold":["c"]}}` with action names lowercase; partial `keys` merge over defaults)
- Behavior of `update`: LEFT/RIGHT emit on the press frame, again when held for `das` frames, then every `arr` frames (`arr == 0` emits LEFT/RIGHT 10 times on the DAS frame); if both are held, only the most recently pressed direction acts; CW/CCW/HARD/HOLD emit once per press; SOFT emits on press then whenever an accumulator (`+= sdf / gravity_frames` per frame, capped at one emit per frame) reaches 1.

- [ ] **Step 1: Write failing tests**
  - `test_tap_emits_once`
  - `test_das_then_arr_schedule`: LEFT held 16 frames with das=10, arr=2 -> frames that emit are `[0, 10, 12, 14]`
  - `test_arr_zero_slides_instantly`: frame 10 returns ten `LEFT`s
  - `test_never_both_directions_in_one_frame` (review focus 3): hold LEFT 5 frames, then add RIGHT -> RIGHT emits immediately and no frame ever contains both
  - `test_release_mid_das_then_repress_moves_immediately`
  - `test_reset_clears_state`: after `reset()` a held LEFT behaves like a fresh press
  - `test_edge_triggered_actions`: CW held 5 frames emits once
  - `test_soft_cadence`: `gravity_frames=60`, `sdf=20`, SOFT held 7 frames -> emits on frames `[0, 3, 6]`
  - Settings: `test_missing_file_gives_defaults` (das 10, arr 2, sdf 20.0, bot_pps 2.5, best_of 3, `keys[Action.CCW] == ["z"]`, `keys[Action.HOLD] == ["c"]`, `keys[Action.CW] == ["up","x"]`); `test_override_values`; `test_partial_keys_merge`; `test_malformed_json_raises_value_error_mentioning_path` (review focus 2); `test_unknown_action_name_raises_value_error_naming_it`; `test_negative_das_raises`; `test_best_of_must_be_odd_positive`
- [ ] **Step 2:** run -> FAIL
- [ ] **Step 3: Implement** both modules.
- [ ] **Step 4:** run -> PASS
- [ ] **Step 5: Commit** `git add tetris/input.py tetris/settings.py tests/test_input.py tests/test_settings.py` / `feat: DAS/ARR input handler and settings loader`

### Task 9: Renderer and playable shell (idle opponent)

**Files:** Create `tetris/ui/__init__.py`, `tetris/ui/render.py`, `tetris/main.py`, `tests/test_main_smoke.py`

**Interfaces:**
- Consumes: `Match`, `Player`, `InputHandler`, `load_settings`
- Produces:
  - `draw_player(surface: pygame.Surface, player: Player, topleft: tuple[int, int], cell: int = 28) -> None` (visible 10x20 field, active piece, ghost, hold box on the left, 5-piece next queue on the right, vertical pending-garbage meter beside the field)
  - `draw_match(surface: pygame.Surface, match: Match, offset: tuple[int, int] = (0, 0)) -> None` (two boards side by side in a 1280x720 frame, win counts)
  - `run(max_frames: int | None = None, opponent: Callable[[Player], list[Action]] | None = None) -> None` in `tetris/main.py` (fixed 60 Hz accumulator loop, `pygame.key.key_code` to map `settings.keys`, Esc quits; `opponent` defaults to returning `[]`; `python -m tetris.main` calls `run()`)

- [ ] **Step 1: Write failing test** `test_run_120_frames_headless`: set `os.environ["SDL_VIDEODRIVER"] = "dummy"` before importing pygame, call `run(max_frames=120)`, assert it returns without raising.
- [ ] **Step 2:** run -> FAIL
- [ ] **Step 3: Implement** `render.py` and `main.py` (primitives only).
- [ ] **Step 4:** `pytest tests/test_main_smoke.py -v` -> PASS. **Manual:** `python -m tetris.main`; confirm arrows move with DAS/ARR, Space hard drops, Up/X rotate CW, Z CCW, C hold, ghost and next queue visible, pieces lock after ~0.5 s grounded.
- [ ] **Step 5: Commit** `git add tetris/ui/__init__.py tetris/ui/render.py tetris/main.py tests/test_main_smoke.py` / `feat: pygame shell with two-board renderer`

### Task 10: Bot placement search

**Files:** Create `tetris/bot/__init__.py`, `tetris/bot/placements.py`, `tests/test_placements.py`

**Interfaces:**
- Consumes: `Board`, `Piece`, `Action`, `tspin_kind`, `SPAWN`
- Produces:
  - `@dataclass(frozen=True) class Placement: piece: Piece; actions: tuple[Action, ...]; tspin: str` (`actions` end with `HARD`)
  - `find_placements(board: Board, kind: str) -> list[Placement]`: BFS from the spawn pose over `LEFT, RIGHT, CW, CCW, SOFT` (one row) using `Board.try_rotate`; state is `(x, y, rot, last_kick)` where `last_kick` is None unless the last move was a rotation; a state is a final placement when it cannot move down; dedupe by final cell set, keeping the shortest action path; `tspin` computed with `tspin_kind` at the final state; returns `[]` if the spawn pose collides.

- [ ] **Step 1: Write failing tests**
  - `test_empty_board_o_has_nine_distinct_x`
  - `test_all_placements_legal`: for each kind on an empty board every `placement.piece` is non-colliding, grounded (`drop_distance == 0`), and `actions[-1] is Action.HARD`
  - `test_replay_reproduces_placement`: for each placement of every kind on a board with some obstacles, a fresh `Player(1)` with `gravity_frames = 1e9`, `board` set, `piece` set to the spawn pose of that kind, fed `placement.actions` (one `step` call with the whole list) locks exactly the cells of `placement.piece`
  - `test_finds_tspin_double`: board = fixture A from Task 3, `find_placements(board, "T")` contains a placement with `piece == Piece("T",1,37,2)` and `tspin == "full"`
  - `test_blocked_spawn_returns_empty`
- [ ] **Step 2:** run -> FAIL
- [ ] **Step 3: Implement** per Interfaces.
- [ ] **Step 4:** run -> PASS
- [ ] **Step 5: Commit** `git add tetris/bot/__init__.py tetris/bot/placements.py tests/test_placements.py` / `feat: bot BFS placement search`

### Task 11: Evaluator and bot

**Files:** Create `tetris/bot/evaluate.py`, `tetris/bot/bot.py`, `tests/test_bot.py`

**Interfaces:**
- Consumes: `find_placements`, `Board`, `attack_lines`, `Player`
- Produces:
  - `@dataclass class Weights` with defaults: `holes=-8.0`, `bumpiness=-0.4`, `aggregate_height=-0.35`, `max_height_over_10=-2.0` (per row above 10), `row_transitions=-0.3`, `well=0.5` (per row of depth of one open edge column, capped at 6), `tspin_slot=2.0`, `attack=3.0` (per attack line), `tspin_clear=4.0`, `b2b_keep=1.5`, `combo=0.5` (per combo step above 1), `pending_garbage=-0.8` (per pending line)
  - `evaluate(board: Board, lines: int, tspin: str, attack: int, combo: int, b2b: bool, pending: int, weights: Weights = Weights()) -> float` (board is the state **after** the lock and clears)
  - `class Bot`: `__init__(pps: float = 2.5, weights: Weights = Weights())`, `actions(player: Player) -> list[Action]` (call once per frame)
- Behavior of `Bot`: when `player.pieces_locked` differs from the last planned piece (or no plan), plan: candidates = placements of the current piece plus (placements of the held piece, or of the next queue piece when the hold is empty) with `HOLD` prepended to their actions; score each as `evaluate` after locking on a `board.copy()` plus the best score over the next queue piece (depth 2, beam of the top 5 per level); choose the best, falling back to `[Action.HARD]` when there are no placements. Pace controller: budget `60 / pps` frames per piece; consecutive `SOFT` actions are emitted together in one frame, every other action takes one slot of `gap = max(1, floor(budget / (non_soft_actions + 1)))` frames; one idle `gap` before the first action.

- [ ] **Step 1: Write failing tests**
  - `test_evaluate_prefers_fewer_holes`: a board with a hole scores lower than the same height without one
  - `test_evaluate_rewards_attack`: same board, `attack=4` scores higher than `attack=0`
  - `test_bot_plays_a_legal_piece`: feed `Bot().actions(player)` each frame to a `Player(3)` for 600 frames with `gravity_frames=1e9`; no exception, `pieces_locked > 5`, `alive` still True
  - `test_bot_pace_close_to_pps`: over 1800 frames at `pps=2.5` (about 75 pieces expected) the bot locks at least 40 pieces
  - `test_bot_no_legal_placement_falls_back` (review focus 5): fill the spawn area so `find_placements` is empty; `Bot().actions(player)` over several frames returns a list and never raises
- [ ] **Step 2:** run -> FAIL
- [ ] **Step 3: Implement** both modules.
- [ ] **Step 4:** run -> PASS
- [ ] **Step 5: Commit** `git add tetris/bot/evaluate.py tetris/bot/bot.py tests/test_bot.py` / `feat: heuristic bot with paced execution`

### Task 12: Wire the bot in and prove matches finish

**Files:** Modify `tetris/main.py`; Create `tests/test_bot_match.py`

**Interfaces:**
- Consumes: `Bot`, `Match`, `load_settings`
- Produces: `run(...)` builds `Bot(pps=settings.bot_pps)` as the default opponent (`opponent=lambda player: bot.actions(player)`), `Match(seed, best_of=settings.best_of)`.

- [ ] **Step 1: Write failing test** `test_bot_vs_bot_round_ends`: for seeds 1, 2, 3, build `Match(seed)` and two `Bot()`s, step up to 60*900 frames feeding each bot its own player's actions; assert `match.round_over` becomes True before the limit and no exception is raised.
- [ ] **Step 2:** run `pytest tests/test_bot_match.py -v` -> FAIL (if the bot cannot yet keep up, or loops forever: investigate before tuning)
- [ ] **Step 3: Implement** the `main.py` wiring; tune `Weights` defaults only if the test shows the bot stalling.
- [ ] **Step 4:** run -> PASS; `pytest -v` for the whole suite -> PASS. **Manual:** `python -m tetris.main`, confirm the bot plays at a human-like pace and sends garbage.
- [ ] **Step 5: Commit** `git add tetris/main.py tests/test_bot_match.py tetris/bot/evaluate.py` / `feat: play against the bot`

### Task 13: Menu flow, match format, effects, README

**Files:** Create `tetris/ui/screens.py`, `tetris/ui/effects.py`, `tests/test_screens.py`, `tests/test_effects.py`, `README.md`; Modify `tetris/main.py`, `tetris/ui/render.py`

**Interfaces:**
- Produces:
  - `class State(Enum)`: `MENU, BATTLE, PAUSED, ROUND_END, MATCH_OVER`
  - `class Flow` (no pygame): `__init__(settings: Settings, seed: int = 0)`, attributes `state: State`, `match: Match | None`, `quit: bool`; `on_key(name: str) -> None` with names `"enter"`, `"escape"`, `"q"`; `update() -> None` that moves `BATTLE -> ROUND_END` when `match.round_over` and `ROUND_END -> MATCH_OVER` when `match.match_winner is not None`. Transitions: `MENU` + enter -> `BATTLE` with a new `Match`; `MENU` + escape -> `quit = True`; `BATTLE` + escape -> `PAUSED`; `PAUSED` + escape -> `BATTLE`; `PAUSED` + q -> `MENU`; `ROUND_END` + enter -> `next_round()` and `BATTLE`; `MATCH_OVER` + enter -> new `Match` and `BATTLE` (rematch); `MATCH_OVER` + escape -> `MENU`.
  - `class Effects`: `__init__(seed: int = 0)`, `on_locks(locks: tuple[LockResult | None, LockResult | None]) -> None`, `update() -> None`, `shake_offset() -> tuple[int, int]`, `flash_rows(side: int) -> list[int]` (rows to flash this frame), `meter_pulse(side: int) -> float` in 0..1. Behavior: a lock with `sent >= 4` starts a shake that decays to `(0, 0)` within 20 updates; cleared rows flash for 6 updates; a pending-garbage increase pulses that side's meter for 12 updates.

- [ ] **Step 1: Write failing tests**
  - Flow: `test_menu_enter_starts_battle`, `test_menu_escape_quits`, `test_pause_and_resume`, `test_pause_q_returns_to_menu`, `test_round_end_then_next_round` (force `match.round_over`, `Flow.update`, enter -> `BATTLE` and `match.round_over is False`), `test_match_over_rematch_resets_wins`
  - Effects: `test_big_attack_shakes_then_settles` (after 20 updates `shake_offset() == (0, 0)`), `test_clear_flash_expires_after_six_updates`, `test_small_attack_does_not_shake`
- [ ] **Step 2:** run -> FAIL
- [ ] **Step 3: Implement** `screens.py` and `effects.py`; in `render.py` add menu, pause, round-end, match-over overlays and apply `Effects` (flash rows, shake offset passed to `draw_match`, meter pulse); in `main.py` drive `Flow`, call `InputHandler.reset()` whenever the state leaves `BATTLE`, and pass `match.last_locks` to `Effects.on_locks`.
- [ ] **Step 4:** `pytest -v` whole suite -> PASS; `README.md` documents install (`pip install -r requirements.txt`), run (`python -m tetris.main`), tests, and the `settings.json` shape from Task 8. **Manual:** play a best-of-3 against the bot: menu -> battle -> pause/resume -> round end -> match over -> rematch; confirm line-clear flash, shake on a 4+ attack, and the garbage meter pulse.
- [ ] **Step 5: Commit** `git add tetris/ui/screens.py tetris/ui/effects.py tetris/ui/render.py tetris/main.py tests/test_screens.py tests/test_effects.py README.md` / `feat: menu flow, match format, effects, docs`
