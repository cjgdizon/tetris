import pytest

from tetris.bot.bot import Bot
from tetris.engine.attack import Batch
from tetris.engine.match import Match
from tetris.engine.player import Player

MAX_FRAMES = 60 * 900


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_bot_vs_bot_round_ends(seed):
    m = Match(seed)
    # Evenly matched bots can stalemate for minutes; a garbage backlog on one side ends the round fast.
    m.players[1].pending = [Batch(8, h) for h in (0, 3, 6, 9, 2, 5, 8, 1)]
    bots = (Bot(), Bot())
    for _ in range(MAX_FRAMES):
        m.step(bots[0].actions(m.players[0]), bots[1].actions(m.players[1]))
        if m.round_over:
            break
    assert m.round_over and m.round_winner == 0 and m.wins == [1, 0]


def test_bot_replans_for_a_new_player():
    bot = Bot()
    first = Player(1)
    first.gravity_frames = 1e9
    for _ in range(10):
        first.step(bot.actions(first))
    second = Player(2)  # fresh player: pieces_locked is 0 again
    second.gravity_frames = 1e9
    for _ in range(120):
        second.step(bot.actions(second))
    assert second.pieces_locked >= 1 and second.alive
