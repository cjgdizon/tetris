from tetris.engine.attack import Batch, attack_lines, cancel, land


def atk(lines, tspin="none", b2b=False, combo=0, pc=False):
    return attack_lines(lines, tspin, b2b, combo, pc)


def test_base_table():
    assert [atk(n) for n in (1, 2, 3, 4)] == [0, 1, 2, 4]
    assert [atk(n, "full") for n in (1, 2, 3)] == [2, 4, 6]
    assert [atk(n, "mini") for n in (1, 2)] == [0, 0]


def test_b2b_bonus():
    assert atk(4, b2b=True) == 5
    assert atk(2, "full", b2b=True) == 5
    assert atk(2, b2b=True) == 1


def test_combo_table():
    assert atk(1, combo=2) == 1
    assert atk(1, combo=5) == 2
    assert atk(1, combo=99) == 5


def test_perfect_clear_is_ten():
    assert atk(4, pc=True) == 10


def test_no_lines_no_attack():
    assert atk(0, combo=5) == 0


def test_cancel():
    p = [Batch(3, 0), Batch(2, 5)]
    assert cancel(p, 4) == 0 and p == [Batch(1, 5)]
    p = [Batch(3, 0), Batch(2, 5)]
    assert cancel(p, 6) == 1 and p == []


def test_land_splits_at_limit():
    p = [Batch(6, 1), Batch(5, 2)]
    assert land(p, 8) == [Batch(6, 1), Batch(2, 2)]
    assert p == [Batch(3, 2)]
