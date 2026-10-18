from tetris.engine.bag import Bag


def test_each_window_of_seven_has_all_kinds():
    b = Bag(1)
    for _ in range(5):
        assert sorted(b.next() for _ in range(7)) == sorted("IOTSZJL")


def test_same_seed_same_sequence():
    a, b = Bag(7), Bag(7)
    assert [a.next() for _ in range(30)] == [b.next() for _ in range(30)]


def test_peek_does_not_consume():
    b = Bag(3)
    p = b.peek(10)
    assert len(p) == 10
    assert [b.next() for _ in range(10)] == p
