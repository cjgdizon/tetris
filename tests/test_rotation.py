from tetris.engine.board import Board
from tetris.engine.pieces import KINDS, Piece


def test_rotate_cw_open_field():
    assert Board().try_rotate(Piece("T", 3, 18, 0), 1) == (Piece("T", 3, 18, 1), 0)


def test_rotate_ccw_open_field():
    assert Board().try_rotate(Piece("T", 3, 18, 0), -1) == (Piece("T", 3, 18, 3), 0)


def test_rotate_uses_first_free_kick():
    b = Board()
    b.cells[32][4] = "X"
    assert b.try_rotate(Piece("T", 3, 30, 0), 1) == (Piece("T", 2, 30, 1), 1)


def test_rotate_none_when_every_kick_blocked():
    b = Board()
    for y in range(40):
        for x in range(10):
            b.cells[y][x] = "X"
    for x, y in Piece("T", 3, 30, 0).cells():
        b.cells[y][x] = None
    assert b.try_rotate(Piece("T", 3, 30, 0), 1) is None


def test_rotate_never_returns_colliding_or_out_of_bounds():
    b = Board()
    for kind in KINDS:
        for x in range(-2, 10):
            for y in range(-3, 4):
                for rot in range(4):
                    for d in (1, -1):
                        res = b.try_rotate(Piece(kind, x, y, rot), d)
                        if res is not None:
                            assert not b.collides(res[0])
                            assert res[0].rot == (rot + d) % 4
