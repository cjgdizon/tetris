from tetris.engine.board import HEIGHT, VISIBLE, WIDTH, Board
from tetris.engine.pieces import Piece


def test_dimensions():
    assert (WIDTH, HEIGHT, VISIBLE) == (10, 40, 20)


def test_collides_walls_floor_ceiling():
    b = Board()
    assert b.collides(Piece("O", -2, 18))
    assert b.collides(Piece("O", 8, 18))
    assert b.collides(Piece("O", 3, 39))
    assert b.collides(Piece("O", 3, -1))
    assert not b.collides(Piece("O", 3, 18))


def test_lock_marks_cells():
    b = Board()
    b.lock(Piece("O", 3, 38))
    assert b.cells[38][4] == "O" and b.cells[39][5] == "O"


def test_lock_and_clear_two_rows():
    b = Board.from_ascii(["XXXXXXXXXX", "XXXXXXXXXX", "X........."])
    assert b.clear_lines() == [37, 38]
    assert b.cells[39][0] == "X"
    assert all(c is None for c in b.cells[38])


def test_add_garbage_shifts_up_with_hole():
    b = Board.from_ascii(["X........."])
    assert b.add_garbage(2, 4) is False
    for y in (38, 39):
        assert [x for x in range(10) if b.cells[y][x] is None] == [4]
        assert b.cells[y][0] == "G"
    assert b.cells[37][0] == "X"


def test_add_garbage_reports_push_out():
    b = Board()
    b.cells[0][0] = "X"
    assert b.add_garbage(1, 0) is True


def test_drop_distance():
    assert Board().drop_distance(Piece("I", 3, 18, 0)) == 20


def test_heights_is_empty_and_copy_independent():
    b = Board.from_ascii(["X.........", "X........."])
    assert b.heights()[0] == 2 and b.heights()[1:] == [0] * 9
    assert Board().is_empty() and not b.is_empty()
    c = b.copy()
    c.cells[39][0] = None
    assert b.cells[39][0] == "X"
