"""Write an acid-style bass line for the Roland S-1 as a MIDI file.

Besides the notes, the file carries filter cutoff (CC74) and resonance (CC71) moves, so a DAW
that plays it back opens and closes the filter like a hand on the knob.

    python -m musictk.hardware.bassline out.mid --bpm 128 --bars 8 --key C --seed 1
"""
from __future__ import annotations

import argparse
import random

import mido

from .common import ACCENT_STEPS, CC_CUTOFF, CC_RESONANCE, S1_CHANNEL, write_midi

KEYS = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
TPB = 480
S16 = TPB // 4

# One bar of semitone offsets from the root (None = rest); minor-pentatonic flavoured.
BASE_BAR = [0, 0, 12, 0, None, 3, 0, 10, 0, -2, 10, -2, 0, None, 7, 3]


def cutoff_at(step: int, total_steps: int) -> int:
    """Cutoff opens 30 -> 100 over the piece, then snaps back toward 40 in the last bar."""
    last_bar = total_steps - 16
    if step < last_bar:
        return int(30 + 70 * step / max(1, last_bar))
    return int(100 - 60 * (step - last_bar) / 16)


def build_events(bars: int, key: str = "C", seed: int = 1) -> list[tuple[int, mido.Message]]:
    root = 36 + KEYS[key]  # C2-based
    rnd = random.Random(seed)
    events: list[tuple[int, mido.Message]] = []
    for bar in range(bars):
        pattern = list(BASE_BAR)
        if bar % 4 == 3:  # vary the 4th bar so the loop does not feel static
            for i in (2, 6, 10, 14):
                pattern[i] = rnd.choice([12, 15, 10, 7])
        for i, offset in enumerate(pattern):
            if offset is None:
                continue
            t = (bar * 16 + i) * S16
            note = root + offset
            vel = 120 if i in ACCENT_STEPS else 85
            events.append((t, mido.Message("note_on", channel=S1_CHANNEL, note=note, velocity=vel)))
            events.append((t + int(S16 * 0.55), mido.Message("note_off", channel=S1_CHANNEL, note=note, velocity=0)))

    total = bars * 16
    for step in range(total):
        events.append((step * S16, mido.Message("control_change", channel=S1_CHANNEL, control=CC_CUTOFF, value=cutoff_at(step, total))))
    for t, value in ((0, 30), (total // 2 * S16, 70), (total * S16, 30)):
        events.append((t, mido.Message("control_change", channel=S1_CHANNEL, control=CC_RESONANCE, value=value)))
    return events


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out")
    ap.add_argument("--bpm", type=float, default=128)
    ap.add_argument("--bars", type=int, default=8)
    ap.add_argument("--key", default="C", choices=list(KEYS))
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args(argv)
    events = build_events(a.bars, a.key, a.seed)
    write_midi(a.out, events, track_name="S-1 Bass", tempo=mido.bpm2tempo(a.bpm), ticks_per_beat=TPB)
    notes = sum(1 for _, m in events if m.type == "note_on")
    print(f"{a.out}: {a.bars} bars, {a.bpm:g} BPM, key {a.key}, {notes} notes")


if __name__ == "__main__":
    main()
