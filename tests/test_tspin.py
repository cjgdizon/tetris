from tetris.engine.board import Board
from tetris.engine.pieces import Piece
from tetris.engine.tspin import tspin_kind

FULL = Board.from_ascii(["...X......", "X...XXXXXX", "XX.XXXXXXX"])
MINI = Board.from_ascii([".X.X......", "X...XXXXXX", "X..XXXXXXX"])
T = Piece("T", 1, 37, 2)


def test_tspin_full():
    assert tspin_kind(FULL, T, True, 0) == "full"


def test_not_rotated_is_none():
    assert tspin_kind(FULL, T, False, 0) == "none"


def test_non_t_is_none():
    assert tspin_kind(FULL, Piece("S", 1, 37, 2), True, 0) == "none"


def test_mini_with_one_front_corner():
    assert tspin_kind(MINI, T, True, 0) == "mini"


def test_mini_upgrades_to_full_on_last_kick():
    assert tspin_kind(MINI, T, True, 4) == "full"


def test_fewer_than_three_corners_is_none():
    assert tspin_kind(Board(), Piece("T", 3, 30, 2), True, 0) == "none"
