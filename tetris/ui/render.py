"""pygame drawing for boards, queues and the match HUD (primitives only, no art)."""
from collections.abc import Collection

import pygame

from tetris.engine.board import HEIGHT, VISIBLE, WIDTH
from tetris.engine.match import Match
from tetris.engine.pieces import SHAPES, Piece
from tetris.engine.player import Action, Player
from tetris.settings import DEFAULT_KEYS, guide_layout

BG = (14, 16, 24)
GRID = (30, 34, 48)
TEXT = (220, 224, 236)
GUIDE_TEXT = (138, 146, 172)
KEY_BORDER = (60, 68, 92)
KEY_BG = (20, 24, 36)
KEY_ACTIVE = (0, 200, 220)
KEY_ACTIVE_BG = (11, 56, 67)
GARBAGE = (110, 110, 120)
METER = (220, 60, 60)
COLORS = {
    "I": (0, 200, 220), "O": (230, 200, 40), "T": (160, 70, 200), "S": (70, 200, 80),
    "Z": (220, 60, 60), "J": (60, 90, 220), "L": (230, 140, 40), "G": GARBAGE, "X": GARBAGE,
}
FIELD_W = 10


def _cell(surface, color, px, py, size):
    pygame.draw.rect(surface, color, (px, py, size - 1, size - 1))


def _mini(surface, kind, left, top, size=18, box=4):
    """Draw a piece (spawn orientation) centered in a box of box*size pixels."""
    cells = SHAPES[kind][0]
    xs = [x for x, _ in cells]
    ys = [y for _, y in cells]
    w, h = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
    ox = left + (box - w) * size // 2
    oy = top + (box - h) * size // 2
    for x, y in cells:
        _cell(surface, COLORS[kind], ox + (x - min(xs)) * size, oy + (y - min(ys)) * size, size)


def draw_player(surface: pygame.Surface, player: Player, topleft: tuple[int, int],
                cell: int = 28, flash_rows: list[int] | None = None, pulse: float = 0.0) -> None:
    x0, y0 = topleft
    fw, fh = WIDTH * cell, VISIBLE * cell
    pygame.draw.rect(surface, GRID, (x0 - 2, y0 - 2, fw + 4, fh + 4), 2)
    for ry in range(VISIBLE, HEIGHT):
        for rx in range(WIDTH):
            kind = player.board.cells[ry][rx]
            if kind is not None:
                _cell(surface, COLORS[kind], x0 + rx * cell, y0 + (ry - VISIBLE) * cell, cell)
    for ry in flash_rows or []:
        if VISIBLE <= ry < HEIGHT:
            pygame.draw.rect(surface, (255, 255, 255), (x0, y0 + (ry - VISIBLE) * cell, fw, cell))
    ghost, piece = player.ghost(), player.piece
    if ghost is not None and player.alive:
        for gx, gy in ghost.cells():
            if gy >= VISIBLE:
                pygame.draw.rect(surface, COLORS[ghost.kind], (x0 + gx * cell, y0 + (gy - VISIBLE) * cell, cell - 1, cell - 1), 2)
    if piece is not None:
        for px, py in piece.cells():
            if py >= VISIBLE - 1:  # one buffer row so a fresh spawn is visible
                _cell(surface, COLORS[piece.kind], x0 + px * cell, y0 + (py - VISIBLE) * cell, cell)
    # hold box (left), next queue (right), garbage meter (between hold and field)
    font = pygame.font.Font(None, 22)
    surface.blit(font.render("HOLD", True, TEXT), (x0 - 122, y0 - 22))
    pygame.draw.rect(surface, GRID, (x0 - 122, y0, 80, 80), 2)
    if player.hold_kind:
        _mini(surface, player.hold_kind, x0 - 122, y0, size=16, box=5)
    surface.blit(font.render("NEXT", True, TEXT), (x0 + fw + 20, y0 - 22))
    for i, kind in enumerate(player.next_kinds(5)):
        _mini(surface, kind, x0 + fw + 20, y0 + i * 70, size=16, box=4)
    pending = sum(b.lines for b in player.pending)
    mh = min(pending, VISIBLE) * cell
    mx = x0 - 30
    width = 12 + int(6 * pulse)
    pygame.draw.rect(surface, GRID, (mx, y0, 12, fh), 1)
    if mh:
        pygame.draw.rect(surface, METER, (mx - (width - 12) // 2, y0 + fh - mh, width, mh))
    if not player.alive:
        surface.blit(pygame.font.Font(None, 48).render("TOPPED OUT", True, METER), (x0 + 30, y0 + fh // 2))


def _draw_keycap(surface: pygame.Surface, rect: pygame.Rect, label: str, font: pygame.font.Font, active: bool) -> None:
    pygame.draw.rect(surface, KEY_ACTIVE_BG if active else KEY_BG, rect)
    pygame.draw.rect(surface, KEY_ACTIVE if active else KEY_BORDER, rect, 2 if active else 1)
    img = font.render(label, True, KEY_ACTIVE if active else TEXT)
    surface.blit(img, (rect.x + (rect.w - img.get_width()) // 2, rect.y + (rect.h - img.get_height()) // 2))


def _draw_guide(surface: pygame.Surface, offset: tuple[int, int],
                keys: dict[Action, list[str]] | None, held: Collection[Action] | None) -> None:
    ox, oy = offset
    guide = guide_layout(DEFAULT_KEYS if keys is None else keys)
    label_font = pygame.font.Font(None, 20)
    cap_font = pygame.font.Font(None, 20)
    caption_font = pygame.font.Font(None, 18)

    surface.blit(label_font.render("CONTROLS", True, TEXT), (20 + ox, 224 + oy))
    slots = {
        "up": (72 + ox, 252 + oy),
        "left": (24 + ox, 286 + oy),
        "down": (72 + ox, 286 + oy),
        "right": (120 + ox, 286 + oy),
    }
    for entry in guide["cluster"]:
        kx, ky = slots[entry["slot"]]
        active = bool(held and Action[entry["action"]] in held)
        _draw_keycap(surface, pygame.Rect(kx, ky, 44, 28), entry["label"], cap_font, active)

    caption = caption_font.render("Move / Soft / CW", True, GUIDE_TEXT)
    surface.blit(caption, (94 + ox - caption.get_width() // 2, 320 + oy))

    for i, row in enumerate(guide["rows"]):
        ry = 352 + oy + i * 34
        cap_w = max(38, cap_font.size(row["cap"])[0] + 14)
        active = bool(row["action"] is not None and held and Action[row["action"]] in held)
        _draw_keycap(surface, pygame.Rect(24 + ox, ry, cap_w, 26), row["cap"], cap_font, active)
        desc = label_font.render(row["desc"], True, TEXT)
        surface.blit(desc, (24 + ox + cap_w + 10, ry + (26 - desc.get_height()) // 2))


def draw_match(surface: pygame.Surface, match: Match, offset: tuple[int, int] = (0, 0),
               flash: tuple[list[int], list[int]] | None = None, pulse: tuple[float, float] = (0.0, 0.0),
               keys: dict[Action, list[str]] | None = None, held: Collection[Action] | None = None) -> None:
    surface.fill(BG)
    ox, oy = offset
    font = pygame.font.Font(None, 30)
    for i, (x, label) in enumerate(((220, "YOU"), (780, "BOT"))):
        draw_player(surface, match.players[i], (x + ox, 110 + oy),
                    flash_rows=flash[i] if flash else None, pulse=pulse[i])
        surface.blit(font.render(f"{label}  wins {match.wins[i]}", True, TEXT), (x + ox, 56 + oy))
    _draw_guide(surface, offset, keys, held)
    info = f"Level {match.level}   Best of {match.best_of}"
    surface.blit(font.render(info, True, TEXT), (560 + ox, 16 + oy))


def overlay_text(flow) -> tuple[str, str] | None:
    """Title and hint for the current overlay, or None while the battle is live."""
    from tetris.ui.screens import State  # local import keeps render free of a screens cycle

    m = flow.match
    if flow.state is State.PAUSED:
        return "PAUSED", "Esc: resume    Q: menu"
    if flow.state is State.ROUND_END:
        title = {None: "DRAW - ROUND REPLAYS", 0: "YOU WIN THE ROUND", 1: "BOT WINS THE ROUND"}[m.round_winner]
        return title, "Enter: next round"
    if flow.state is State.MATCH_OVER:
        title = "YOU WIN THE MATCH" if m.match_winner == 0 else "BOT WINS THE MATCH"
        return title, "Enter: rematch    Esc: menu"
    return None


def _centered(surface, text, size, y, color=TEXT):
    img = pygame.font.Font(None, size).render(text, True, color)
    surface.blit(img, ((surface.get_width() - img.get_width()) // 2, y))


def draw_menu(surface: pygame.Surface) -> None:
    surface.fill(BG)
    _centered(surface, "TETRIS BATTLE", 110, 200)
    _centered(surface, "Enter: play vs bot", 44, 360)
    _centered(surface, "Esc: quit", 44, 410)
    _centered(surface, "Arrows move  -  Up/X rotate  -  Z rotate back  -  C hold  -  Space hard drop", 28, 560, GRID)


def draw_overlay(surface: pygame.Surface, title: str, hint: str) -> None:
    shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 170))
    surface.blit(shade, (0, 0))
    _centered(surface, title, 84, 280)
    _centered(surface, hint, 36, 380)


def draw_flow(surface: pygame.Surface, flow, effects, held: Collection[Action] | None = None) -> None:
    from tetris.ui.screens import State

    if flow.state is State.MENU:
        draw_menu(surface)
        return
    draw_match(surface, flow.match, effects.shake_offset(),
               flash=(effects.flash_rows(0), effects.flash_rows(1)),
               pulse=(effects.meter_pulse(0), effects.meter_pulse(1)),
               keys=flow.settings.keys, held=held)
    text = overlay_text(flow)
    if text:
        draw_overlay(surface, *text)
