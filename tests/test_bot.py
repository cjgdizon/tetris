from tetris.bot.bot import Bot
from tetris.bot.evaluate import Weights, evaluate
from tetris.bot.placements import drop_placements, find_placements
from tetris.engine.board import Board
from tetris.engine.pieces import KINDS, Piece
from tetris.engine.player import Action, Player


def score(board, **kw):
    args = dict(lines=0, tspin="none", attack=0, combo=0, b2b=False, pending=0)
    args.update(kw)
    return evaluate(board, **args)


def test_evaluate_prefers_fewer_holes():
    hole = Board.from_ascii(["X.........", ".........."])
    solid = Board.from_ascii(["X.........", "X........."])
    assert score(solid) > score(hole)


def test_evaluate_rewards_attack():
    b = Board.from_ascii(["X........."])
    assert score(b, attack=4) > score(b, attack=0)


def test_evaluate_penalizes_pending_garbage():
    b = Board.from_ascii(["X........."])
    assert score(b, pending=4) < score(b, pending=0)


def test_evaluate_rewards_tspin_pocket():
    pocket = Board.from_ascii(["...X......", "X...XXXXXX", "XX.XXXXXXX"])
    flat = Board.from_ascii([".........." , "XXXXXXXXXX".replace("X", ".", 3), "XXXXXXXXXX".replace("X", ".", 3)])
    w = Weights(holes=0, bumpiness=0, aggregate_height=0, max_height_over_10=0, row_transitions=0, well=0)
    assert evaluate(pocket, 0, "none", 0, 0, False, 0, w) > evaluate(flat, 0, "none", 0, 0, False, 0, w)


def test_drop_placements_are_legal():
    b = Board.from_ascii(["X.........", "XX........"])
    for kind in KINDS:
        poses = drop_placements(b, kind)
        assert poses
        for p in poses:
            assert not b.collides(p) and b.drop_distance(p) == 0


def test_bot_plays_a_legal_piece():
    p = Player(3)
    p.gravity_frames = 1e9
    bot = Bot()
    for _ in range(600):
        p.step(bot.actions(p))
    assert p.pieces_locked > 5 and p.alive


def test_bot_pace_close_to_pps():
    p = Player(5)
    p.gravity_frames = 1e9
    bot = Bot(pps=2.5)
    for _ in range(1800):
        p.step(bot.actions(p))
    assert 40 <= p.pieces_locked <= 100 and p.alive


def test_bot_holds_only_once_per_piece():
    p = Player(2)
    p.gravity_frames = 1e9
    bot = Bot()
    for _ in range(300):
        p.step(bot.actions(p))
    assert p.alive


def test_bot_no_legal_placement_falls_back():
    p = Player(1)
    p.gravity_frames = 1e9
    p.board.cells[19][4] = "X"
    p.board.cells[18][4] = "X"
    bot = Bot()
    for _ in range(40):
        out = bot.actions(p)
        assert isinstance(out, list)
