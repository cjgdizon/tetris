from tetris.engine.player import LockResult
from tetris.ui.effects import Effects


def lock(sent=0, rows=()):
    return LockResult(lines=len(rows), tspin="none", sent=sent, cancelled=0, perfect_clear=False,
                      cleared_rows=list(rows), garbage_landed=0)


def test_big_attack_shakes_then_settles():
    e = Effects(1)
    e.on_locks((lock(sent=4, rows=[36, 37, 38, 39]), None))
    assert any(e.shake_offset() != (0, 0) for _ in range(5))
    for _ in range(20):
        e.update()
    assert e.shake_offset() == (0, 0)


def test_small_attack_does_not_shake():
    e = Effects(1)
    e.on_locks((lock(sent=3, rows=[38, 39]), None))
    assert e.shake_offset() == (0, 0)


def test_clear_flash_expires_after_six_updates():
    e = Effects(1)
    e.on_locks((None, lock(rows=[38, 39])))
    assert e.flash_rows(1) == [38, 39] and e.flash_rows(0) == []
    for _ in range(5):
        e.update()
    assert e.flash_rows(1) == [38, 39]
    e.update()
    assert e.flash_rows(1) == []


def test_pending_increase_pulses_meter_then_fades():
    e = Effects(1)
    e.on_pending((0, 0))
    e.on_pending((4, 0))
    assert e.meter_pulse(0) == 1.0 and e.meter_pulse(1) == 0.0
    for _ in range(12):
        e.update()
    assert e.meter_pulse(0) == 0.0


def test_pending_decrease_does_not_pulse():
    e = Effects(1)
    e.on_pending((4, 0))
    for _ in range(12):
        e.update()
    e.on_pending((2, 0))
    assert e.meter_pulse(0) == 0.0
