"""Play a short acid bass line on a Roland S-1 live, sweeping the filter as it goes.

    python -m musictk.hardware.jam --bpm 120 --bars 4
"""
from __future__ import annotations

import argparse
import time

import mido

from .common import ACCENT_STEPS, CC_CUTOFF, CC_RESONANCE, S1_CHANNEL

# C minor phrase, 16 steps per bar (None = rest).
PATTERN = [36, 36, 48, 36, None, 39, 36, 46,
           36, 34, 46, 34, 36, None, 43, 39]


def cutoff_at(step: int, total_steps: int) -> int:
    """Open the filter 30 -> 100, then close it again over the last bar."""
    last_bar = total_steps - 16
    x = step / last_bar if step < last_bar else 1 - (step - last_bar) / 16
    return int(30 + 70 * min(1, x))


def note_for(step: int, total_steps: int) -> int | None:
    """Pattern note for a step; the last bar jumps an octave on every 4th step."""
    n = PATTERN[step % 16]
    if n is not None and step >= total_steps - 16 and step % 4 == 2:
        n += 12
    return n


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bpm", type=float, default=120)
    ap.add_argument("--bars", type=int, default=4)
    ap.add_argument("--port", default="S-1 MIDI IN")
    a = ap.parse_args(argv)
    if a.bars < 2:
        ap.error("--bars must be at least 2")

    step_len = 60 / a.bpm / 4
    total = 16 * a.bars
    with mido.open_output(a.port) as out:
        def cc(num: int, val: int) -> None:
            out.send(mido.Message("control_change", channel=S1_CHANNEL, control=num, value=int(val)))

        cc(CC_RESONANCE, 30)
        t0 = time.time()
        for i in range(total):
            cc(CC_CUTOFF, cutoff_at(i, total))
            if i == total // 2:
                cc(CC_RESONANCE, 70)
            n = note_for(i, total)
            if n is not None:
                vel = 120 if i % 16 in ACCENT_STEPS else 85
                out.send(mido.Message("note_on", channel=S1_CHANNEL, note=n, velocity=vel))
                time.sleep(step_len * 0.55)
                out.send(mido.Message("note_off", channel=S1_CHANNEL, note=n))
            wait = t0 + (i + 1) * step_len - time.time()
            if wait > 0:
                time.sleep(wait)
        cc(CC_CUTOFF, 40)
        cc(CC_RESONANCE, 30)


if __name__ == "__main__":
    main()
