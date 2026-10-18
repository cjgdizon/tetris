from tetris.engine.pieces import Piece
from tetris.engine.player import Action, Player


def fresh(seed=1, **kw):
    p = Player(seed, **kw)
    p.gravity_frames = kw.get("gravity_frames", 1e9)
    return p


def test_spawn_pose():
    p = Player(1)
    assert (p.piece.x, p.piece.y, p.piece.rot) == (3, 18, 0)


def test_left_moves_and_wall_blocks():
    p = fresh()
    p.piece = Piece("T", 3, 18, 0)
    for _ in range(3):
        p.step([Action.LEFT])
    assert p.piece.x == 0
    p.step([Action.LEFT])
    assert p.piece.x == 0


def test_hard_drop_locks_and_spawns():
    p = fresh()
    p.step([Action.HARD])
    assert p.pieces_locked == 1
    assert any(c is not None for c in p.board.cells[39])
    assert (p.piece.x, p.piece.y, p.piece.rot) == (3, 18, 0)


def test_gravity_one_row_per_n_frames():
    p = fresh(gravity_frames=2)
    p.gravity_frames = 2
    y = p.piece.y
    p.step([])
    assert p.piece.y == y
    p.step([])
    assert p.piece.y == y + 1


def test_lock_delay_30_frames():
    p = fresh()
    p.piece = Piece("O", 3, 38, 0)
    for _ in range(29):
        p.step([])
    assert p.pieces_locked == 0
    p.step([])
    assert p.pieces_locked == 1


def test_move_reset_cap():
    p = fresh()
    p.piece = Piece("O", 3, 38, 0)
    for i in range(60):
        p.step([Action.LEFT if i % 2 == 0 else Action.RIGHT])
        if p.pieces_locked:
            break
    assert p.pieces_locked >= 1


def test_move_resets_lock_timer_a_few_times():
    p = fresh()
    p.piece = Piece("O", 3, 38, 0)
    for i in range(40):
        p.step([Action.LEFT] if i % 10 == 0 else [])
    # moves every 10 frames keep resetting the timer, so it has not locked yet
    assert p.pieces_locked == 0


def test_hold_once_per_piece():
    p = fresh(seed=5)
    first = p.piece.kind
    nxt = p.next_kinds(1)[0]
    p.step([Action.HOLD])
    assert p.hold_kind == first and p.piece.kind == nxt
    p.step([Action.HOLD])
    assert p.hold_kind == first and p.piece.kind == nxt
    p.step([Action.HARD])
    cur = p.piece.kind
    p.step([Action.HOLD])
    assert p.hold_kind == cur and p.piece.kind == first


def test_ghost_equals_hard_drop_pose():
    p = fresh()
    assert p.ghost() == p.piece.moved(0, p.board.drop_distance(p.piece))


def test_soft_moves_exactly_one_row():
    p = fresh()
    y = p.piece.y
    p.step([Action.SOFT])
    assert p.piece.y == y + 1


def test_cw_sets_last_move_rotation():
    p = fresh()
    p.piece = Piece("T", 3, 18, 0)
    p.step([Action.CW])
    assert p.piece.rot == 1 and p.last_move_rotation is True
    p.step([Action.LEFT])
    assert p.last_move_rotation is False
