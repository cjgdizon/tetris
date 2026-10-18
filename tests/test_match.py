from tetris.engine.attack import Batch
from tetris.engine.board import Board
from tetris.engine.match import Match, gravity_for_level
from tetris.engine.pieces import Piece
from tetris.engine.player import Action


def setup_tetris(player):
    player.board = Board.from_ascii(["X........."] + ["XXXXXXXXX."] * 4)
    player.piece = Piece("I", 7, 36, 1)


def test_players_share_piece_sequence():
    m = Match(1)
    assert m.players[0].next_kinds() == m.players[1].next_kinds()


def test_tetris_routes_garbage_to_opponent():
    m = Match(1)
    setup_tetris(m.players[0])
    m.step([Action.HARD], [])
    (b,) = m.players[1].pending
    assert b.lines == 4 and 0 <= b.hole < 10
    assert m.last_locks[0].sent == 4 and m.last_locks[1] is None


def test_garbage_cancelled_before_sending():
    m = Match(1)
    setup_tetris(m.players[0])
    m.players[0].pending = [Batch(4, 0)]
    m.step([Action.HARD], [])
    assert m.players[1].pending == [] and m.players[0].pending == []


def test_level_speeds_up():
    m = Match(1)
    for _ in range(1800):
        m.step([], [])
    assert abs(gravity_for_level(2) - 60 * 0.793) < 1e-9
    assert abs(m.players[0].gravity_frames - gravity_for_level(2)) < 1e-9
    m.frame = 100000
    assert m.level == 15


def test_simultaneous_top_out_replays_round():
    m = Match(1)
    m.players[0].alive = False
    m.players[1].alive = False
    m.step([], [])
    assert m.round_over is True and m.round_winner is None and m.wins == [0, 0]
    m.next_round()
    assert m.round_over is False and m.players[0].board.is_empty()


def test_best_of_three_winner():
    m = Match(1)
    m.players[1].alive = False
    m.step([], [])
    assert m.wins == [1, 0] and m.round_winner == 0 and m.match_winner is None
    m.next_round()
    m.players[1].alive = False
    m.step([], [])
    assert m.wins == [2, 0] and m.match_winner == 0


def test_step_is_noop_after_round_over():
    m = Match(1)
    m.players[1].alive = False
    m.step([], [])
    frame = m.frame
    m.step([], [])
    assert m.frame == frame and m.wins == [1, 0]
