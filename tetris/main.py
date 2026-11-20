"""Fixed 60 Hz game loop. Run with: python -m tetris.main"""
from collections.abc import Callable

import pygame

from tetris.engine.player import Action, Player
from tetris.session import GameSession
from tetris.settings import Settings, load_settings
from tetris.ui.render import draw_flow
from tetris.ui.screens import State

WINDOW = (1280, 720)
FLOW_KEYS = {pygame.K_RETURN: "enter", pygame.K_KP_ENTER: "enter", pygame.K_ESCAPE: "escape", pygame.K_q: "q"}


def _keymap(settings: Settings) -> dict[Action, list[int]]:
    keymap: dict[Action, list[int]] = {}
    for action, names in settings.keys.items():
        codes = []
        for name in names:
            try:
                codes.append(pygame.key.key_code(name))
            except ValueError:
                raise ValueError(f"settings: unknown key name {name!r} for {action.name.lower()}") from None
        keymap[action] = codes
    return keymap


def run(max_frames: int | None = None,
        opponent: Callable[[Player], list[Action]] | None = None,
        settings: Settings | None = None,
        start_in_battle: bool = False) -> None:
    pygame.init()
    try:
        settings = settings or load_settings()
        keymap = _keymap(settings)
        screen = pygame.display.set_mode(WINDOW)
        pygame.display.set_caption("Tetris Battle")
        session = GameSession(settings=settings, opponent=opponent)
        if start_in_battle:
            session.on_flow_key("enter")
        clock = pygame.time.Clock()
        frames, running = 0, True
        while running and (max_frames is None or frames < max_frames):
            dt = clock.tick(120) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key in FLOW_KEYS:
                    session.on_flow_key(FLOW_KEYS[event.key])
            running = running and not session.flow.quit
            pressed = pygame.key.get_pressed()
            held = {a for a, codes in keymap.items() if any(pressed[c] for c in codes)}
            remaining = None if max_frames is None else max_frames - frames
            frames += session.step(dt, held, max_ticks=remaining)
            draw_flow(screen, session.flow, session.effects, held=held if session.flow.state is State.BATTLE else None)
            pygame.display.flip()
    finally:
        pygame.quit()


def main() -> None:
    try:
        run()
    except ValueError as e:  # bad settings.json: show the message, not a traceback
        raise SystemExit(f"error: {e}") from None


if __name__ == "__main__":
    main()
