"""Attack table, combo/back-to-back and garbage batch handling."""
from dataclasses import dataclass

COMBO_TABLE = [0, 0, 1, 1, 1, 2, 2, 3, 3, 4, 4, 4, 5]
_BASE = {1: 0, 2: 1, 3: 2, 4: 4}
_TSPIN_FULL = {1: 2, 2: 4, 3: 6}
PERFECT_CLEAR = 10


@dataclass
class Batch:
    lines: int
    hole: int


def is_difficult(lines: int, tspin: str) -> bool:
    return lines > 0 and (lines == 4 or tspin != "none")


def attack_lines(lines: int, tspin: str, b2b: bool, combo: int, perfect_clear: bool) -> int:
    if lines == 0:
        return 0
    if perfect_clear:
        return PERFECT_CLEAR
    if tspin == "mini":
        base = 0
    elif tspin == "full":
        base = _TSPIN_FULL[lines]
    else:
        base = _BASE[lines]
    if b2b and is_difficult(lines, tspin):
        base += 1
    return base + COMBO_TABLE[min(combo, len(COMBO_TABLE) - 1)]


def cancel(pending: list[Batch], attack: int) -> int:
    """Cancel pending garbage FIFO with an attack; returns the leftover attack."""
    while pending and attack > 0:
        b = pending[0]
        used = min(b.lines, attack)
        b.lines -= used
        attack -= used
        if b.lines == 0:
            pending.pop(0)
    return attack


def land(pending: list[Batch], limit: int = 8) -> list[Batch]:
    """Take up to `limit` garbage lines FIFO out of pending."""
    out: list[Batch] = []
    while pending and limit > 0:
        b = pending[0]
        if b.lines <= limit:
            out.append(pending.pop(0))
            limit -= b.lines
        else:
            out.append(Batch(limit, b.hole))
            b.lines -= limit
            limit = 0
    return out
