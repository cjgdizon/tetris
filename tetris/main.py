"""Fixed 60 Hz game loop. Run with: python -m tetris.main"""
import time
from collections.abc import Callable

import pygame

from tetris.bot.bot import Bot
from tetris.engine.player import Action, Player
from tetris.input import InputHandler
from tetris.settings import Settings, load_settings
from tetris.ui.effects import Effects
from tetris.ui.render import draw_flow
from tetris.ui.screens import Flow, State

TICK = 1 / 60
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
        handler = InputHandler(settings.handling)
        flow = Flow(settings, seed=int(time.time()))
        if start_in_battle:
            flow.on_key("enter")
        effects = Effects(seed=1)
        opponent = opponent or Bot(pps=settings.bot_pps).actions
        clock = pygame.time.Clock()
        acc, frames, running = 0.0, 0, True
        while running and (max_frames is None or frames < max_frames):
            acc = min(acc + clock.tick(120) / 1000, 5 * TICK)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key in FLOW_KEYS:
                    was_battle = flow.state is State.BATTLE
                    flow.on_key(FLOW_KEYS[event.key])
                    if was_battle != (flow.state is State.BATTLE):
                        handler.reset()
            running = running and not flow.quit
            pressed = pygame.key.get_pressed()
            held = {a for a, codes in keymap.items() if any(pressed[c] for c in codes)}
            while acc >= TICK and (max_frames is None or frames < max_frames):
                acc -= TICK
                frames += 1
                if flow.state is State.BATTLE:
                    match = flow.match
                    human = handler.update(held, match.players[0].gravity_frames)
                    match.step(human, opponent(match.players[1]))
                    effects.on_locks(match.last_locks)
                    effects.on_pending(tuple(sum(b.lines for b in p.pending) for p in match.players))
                    flow.update()
                    if flow.state is not State.BATTLE:
                        handler.reset()
                effects.update()
            draw_flow(screen, flow, effects)
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
