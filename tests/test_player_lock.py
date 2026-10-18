from tetris.engine.attack import Batch
from tetris.engine.board import Board
from tetris.engine.pieces import Piece
from tetris.engine.player import Action, Player


def new_player():
    p = Player(1)
    p.gravity_frames = 1e9
    return p


def setup_tetris(p, extra=True):
    p.board = Board.from_ascii((["X........."] if extra else []) + ["XXXXXXXXX."] * 4)
    p.piece = Piece("I", 7, 36, 1)


def hard(p):
    return p.step([Action.HARD])


def test_tetris_sends_four():
    p = new_player()
    setup_tetris(p)
    r = hard(p)
    assert (r.lines, r.sent, r.perfect_clear) == (4, 4, False)
    assert r.cleared_rows == [36, 37, 38, 39]


def test_second_tetris_gets_b2b():
    p = new_player()
    sent = []
    for _ in range(2):
        setup_tetris(p)
        sent.append(hard(p).sent)
    assert sent == [4, 5]


def test_combo_sequence():
    p = new_player()
    sent = []
    for _ in range(3):
        p.board = Board.from_ascii(["XXXXXXXXX."])
        p.piece = Piece("I", 7, 36, 1)
        sent.append(hard(p).sent)
    assert sent == [0, 0, 1]


def test_perfect_clear_ten():
    p = new_player()
    setup_tetris(p, extra=False)
    r = hard(p)
    assert r.perfect_clear and r.sent == 10


def test_tspin_double():
    p = new_player()
    p.board = Board.from_ascii(["...X......", "X...XXXXXX", "XX.XXXXXXX"])
    p.piece = Piece("T", 1, 37, 2)
    p.last_move_rotation, p.last_kick = True, 0
    r = hard(p)
    assert (r.lines, r.tspin, r.sent) == (2, "full", 4)


def test_no_clear_lands_garbage_max_eight():
    p = new_player()
    p.piece = Piece("O", 3, 18, 0)
    p.pending = [Batch(10, 3)]
    r = hard(p)
    assert r.garbage_landed == 8 and p.pending == [Batch(2, 3)]
    for y in range(32, 40):
        assert [x for x in range(10) if p.board.cells[y][x] is None] == [3]


def test_clear_cancels_pending():
    p = new_player()
    setup_tetris(p)
    p.pending = [Batch(3, 0)]
    r = hard(p)
    assert (r.sent, r.cancelled, r.garbage_landed) == (1, 3, 0)
    assert p.pending == []


def test_lock_out_above_visible():
    p = new_player()
    p.board = Board.from_ascii(["XXXXXXXXX."] * 20)
    p.piece = Piece("O", 3, 10, 0)
    hard(p)
    assert p.alive is False


def test_block_out_on_spawn():
    p = new_player()
    p.board.cells[19][4] = "X"
    p.piece = Piece("O", 0, 30, 0)
    hard(p)
    assert p.alive is False


def test_garbage_push_out():
    p = new_player()
    p.board.cells[3][0] = "X"
    p.piece = Piece("O", 3, 18, 0)
    p.pending = [Batch(8, 0)]
    hard(p)
    assert p.alive is False


def test_b2b_survives_a_lock_without_clear():
    p = new_player()
    setup_tetris(p)
    hard(p)
    p.board = Board()
    p.piece = Piece("O", 3, 18, 0)
    hard(p)  # no clear, b2b must remain
    setup_tetris(p)
    assert hard(p).sent == 5
