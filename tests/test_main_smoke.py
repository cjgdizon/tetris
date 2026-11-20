import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402

from tetris.engine.player import Action  # noqa: E402
from tetris.main import run  # noqa: E402
from tetris.settings import load_settings  # noqa: E402
from tetris.ui.effects import Effects  # noqa: E402
from tetris.ui.render import KEY_ACTIVE, draw_flow  # noqa: E402
from tetris.ui.screens import Flow, State  # noqa: E402


def test_run_120_frames_headless_menu():
    run(max_frames=120)


def test_run_300_frames_headless_battle_against_bot():
    run(max_frames=300, start_in_battle=True)


def test_draw_flow_every_state(tmp_path):
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    flow = Flow(load_settings(tmp_path / "none.json"), seed=1)
    fx = Effects()
    draw_flow(screen, flow, fx)  # menu
    flow.on_key("enter")
    draw_flow(screen, flow, fx)  # battle
    flow.on_key("escape")
    assert flow.state is State.PAUSED
    draw_flow(screen, flow, fx)
    flow.on_key("escape")
    flow.match.players[1].alive = False
    flow.match.step([], [])
    flow.update()
    draw_flow(screen, flow, fx)  # round end
    flow.on_key("enter")
    flow.match.players[1].alive = False
    flow.match.step([], [])
    flow.update()
    assert flow.state is State.MATCH_OVER
    draw_flow(screen, flow, fx)  # match over
    pygame.quit()


def test_draw_flow_battle_highlights_held_keys(tmp_path):
    pygame.init()
    try:
        screen = pygame.display.set_mode((1280, 720))
        flow = Flow(load_settings(tmp_path / "none.json"), seed=1)
        flow.on_key("enter")
        fx = Effects()

        draw_flow(screen, flow, fx)
        assert screen.get_at((24, 286))[:3] != KEY_ACTIVE
        assert screen.get_at((24, 454))[:3] != KEY_ACTIVE

        draw_flow(screen, flow, fx, held={Action.LEFT, Action.HARD})
        assert screen.get_at((24, 286))[:3] == KEY_ACTIVE
        assert screen.get_at((24, 454))[:3] == KEY_ACTIVE
    finally:
        pygame.quit()
