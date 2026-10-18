from tetris.engine.pieces import KICKS, KINDS, SHAPES, SPAWN, Piece


def test_every_kind_has_four_states_of_four_cells():
    for k in KINDS:
        assert len(SHAPES[k]) == 4
        assert all(len(s) == 4 for s in SHAPES[k])


def test_t_spawn_cells():
    assert sorted(Piece("T", 3, 18, 0).cells()) == [(3, 19), (4, 18), (4, 19), (5, 19)]


def test_i_spawn_cells():
    assert sorted(Piece("I", 3, 18, 0).cells()) == [(3, 19), (4, 19), (5, 19), (6, 19)]


def test_o_spawn_cells():
    assert sorted(Piece("O", 3, 18, 0).cells()) == [(4, 18), (4, 19), (5, 18), (5, 19)]


def test_spawn_constant():
    assert SPAWN == (3, 18)


def test_states_are_distinct_except_o():
    for k in "TSZJLI":
        assert len({frozenset(s) for s in SHAPES[k]}) == 4
    assert len({frozenset(s) for s in SHAPES["O"]}) == 1


def test_kick_tables_pinned():
    assert KICKS["JLSTZ"][(0, 1)] == [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)]
    assert KICKS["JLSTZ"][(3, 0)] == [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)]
    assert KICKS["I"][(0, 1)] == [(0, 0), (-2, 0), (1, 0), (-2, 1), (1, -2)]


def test_all_transitions_have_five_kicks():
    for table in ("JLSTZ", "I"):
        for a in range(4):
            for b in ((a + 1) % 4, (a - 1) % 4):
                assert len(KICKS[table][(a, b)]) == 5
