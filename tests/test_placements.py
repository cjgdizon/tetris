from tetris.bot.placements import find_placements
from tetris.engine.board import Board
from tetris.engine.pieces import KINDS, SPAWN, Piece
from tetris.engine.player import Action, Player

OBSTACLES = ["X.........", "XX........", "XXX......."]


def test_empty_board_o_has_nine_distinct_x():
    ps = find_placements(Board(), "O")
    assert len(ps) == 9 and len({p.piece.x for p in ps}) == 9


def test_all_placements_legal():
    b = Board()
    for kind in KINDS:
        ps = find_placements(b, kind)
        assert ps
        for p in ps:
            assert not b.collides(p.piece)
            assert b.drop_distance(p.piece) == 0
            assert p.actions[-1] is Action.HARD


def test_replay_reproduces_placement():
    b = Board.from_ascii(OBSTACLES)
    for kind in KINDS:
        for pl in find_placements(b, kind):
            player = Player(1)
            player.gravity_frames = 1e9
            player.board = b.copy()
            player.piece = Piece(kind, *SPAWN, 0)
            player.step(list(pl.actions))
            got = {(x, y) for y in range(40) for x in range(10) if player.board.cells[y][x] == kind}
            assert got == set(pl.piece.cells()), (kind, pl)


def test_finds_tspin_double():
    b = Board.from_ascii(["...X......", "X...XXXXXX", "XX.XXXXXXX"])
    ps = find_placements(b, "T")
    assert any(p.piece == Piece("T", 1, 37, 2) and p.tspin == "full" for p in ps)


def test_blocked_spawn_returns_empty():
    b = Board()
    b.cells[19][4] = "X"
    assert find_placements(b, "T") == []


# Characterization: placement counts per board, recorded from the plain one-row-at-a-time BFS.
# They pin behavior so BFS speed-ups cannot silently drop reachable placements.
COUNTS = {
    "empty": ([], {"I": 17, "O": 9, "T": 34, "S": 17, "Z": 17, "J": 34, "L": 34}, 0),
    "stairs": (["X.........", "XX........", "XXX......."], {"I": 17, "O": 9, "T": 34, "S": 17, "Z": 17, "J": 34, "L": 34}, 0),
    "tsd": (["...X......", "X...XXXXXX", "XX.XXXXXXX"], {"I": 17, "O": 9, "T": 38, "S": 17, "Z": 18, "J": 34, "L": 35}, 4),
    "overhang": (["XXXX......", "..........", "XXXXXX...."], {"I": 21, "O": 9, "T": 35, "S": 18, "Z": 17, "J": 35, "L": 36}, 0),
}


def test_placement_counts_are_stable():
    for name, (rows, counts, spins) in COUNTS.items():
        b = Board.from_ascii(rows) if rows else Board()
        assert {k: len(find_placements(b, k)) for k in KINDS} == counts, name
        assert sum(1 for p in find_placements(b, "T") if p.tspin != "none") == spins, name
