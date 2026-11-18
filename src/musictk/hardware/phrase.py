"""Follow a Roland P-6 bass line with an S-1 acid phrase, written as a MIDI file.

The lowest note of each bar in the P-6 bass file is taken as that bar's chord root; the S-1
riff is transposed onto it. Bars where the bass is silent stay silent. Every section in
``SECTIONS`` picks a riff and a cutoff/resonance move.

    python -m musictk.hardware.phrase p6_bass.mid out.mid
"""
from __future__ import annotations

import argparse

import mido

from .common import CC_CUTOFF, CC_RESONANCE, S1_CHANNEL, write_midi

# Riffs: 16 sixteenth-note steps. int = semitones from the root, None = rest, "+" = hold.
RIFF: dict[str, list] = {
    "pulse": [0, None] * 8,
    "sparse": [0, None, None, None, None, None, 12, None, None, None, 0, None, None, None, None, None],
    "A": [0, 0, 12, 0, None, 7, 0, 10, 0, None, 12, 0, 3, None, 7, 0],
    "B": [0, 12, 0, 15, 0, 7, 12, None, 0, 10, 12, 0, 19, 12, 7, 3],
    "hold": [0, "+", "+", "+", "+", "+", "+", "+", 7, "+", "+", "+", 12, "+", "+", "+"],
}
ACCENT = {0, 3, 6, 10, 13}

# (first bar, last bar, riff, cutoff start, cutoff end, resonance), bars counted from 1.
SECTIONS = [
    (9, 16, "pulse", 25, 45, 40),
    (17, 32, "A", 40, 80, 60),
    (33, 40, "hold", 30, 30, 50),
    (41, 56, "B", 50, 95, 80),
    (57, 64, "sparse", 35, 35, 50),
    (65, 72, "A", 30, 70, 60),
    (73, 88, "B", 60, 100, 85),
    (89, 96, "B", 90, 110, 100),
    (97, 112, "A", 70, 50, 70),
    (113, 120, "pulse", 50, 30, 50),
]


def chord_shift(root: int, offset: int) -> int:
    """Roots other than C (the Ab / Bb bars) turn the minor third into a major third."""
    if root % 12 != 0 and offset % 12 == 3:
        return offset + 1
    return offset


def bar_roots(notes: list[tuple[int, int]], bar_ticks: int) -> list[int | None]:
    """Lowest note per bar from ``(tick, note)`` pairs; None where nothing plays."""
    n_bars = max(t for t, _ in notes) // bar_ticks + 1
    return [
        min((n for t, n in notes if b * bar_ticks <= t < (b + 1) * bar_ticks), default=None)
        for b in range(n_bars)
    ]


def hold_length(pattern: list, index: int) -> int:
    """How many steps a note at ``index`` lasts (itself plus following "+" holds)."""
    span = 1
    while index + span < 16 and pattern[index + span] == "+":
        span += 1
    return span


def build_events(roots, tpb, sections=SECTIONS) -> list[tuple[int, mido.Message]]:
    bar, s16 = tpb * 4, tpb // 4
    ev: list[tuple[int, mido.Message]] = []

    def cc(t, control, value):
        ev.append((t, mido.Message("control_change", channel=S1_CHANNEL, control=control, value=value)))

    cc(0, CC_CUTOFF, sections[0][3])
    cc(0, CC_RESONANCE, sections[0][5])
    for first, last, riff, f0, f1, reso in sections:
        cc((first - 1) * bar, CC_RESONANCE, reso)
        length = (last - first + 1) * 16
        pattern = RIFF[riff]
        for k in range(length):
            b = first - 1 + k // 16
            if b >= len(roots):
                break
            t = b * bar + (k % 16) * s16
            cc(t, CC_CUTOFF, int(f0 + (f1 - f0) * k / max(1, length - 1)))
            root = roots[b]
            offset = pattern[k % 16]
            if root is None or offset is None or offset == "+":
                continue
            span = hold_length(pattern, k % 16)
            base = 48 + (root % 12) - (12 if root % 12 > 7 else 0)
            note = base + chord_shift(root, offset)
            vel = 120 if (k % 16) in ACCENT else 88
            gate = s16 * span - s16 // 4 if span > 1 else int(s16 * 0.55)
            ev.append((t, mido.Message("note_on", channel=S1_CHANNEL, note=note, velocity=vel)))
            ev.append((t + gate, mido.Message("note_off", channel=S1_CHANNEL, note=note, velocity=0)))
    end = sections[-1][1] * bar
    cc(end, CC_CUTOFF, 40)
    cc(end, CC_RESONANCE, 30)
    return ev


def read_bass(path: str) -> tuple[int, int, list[tuple[int, int]]]:
    """Return ``(ticks_per_beat, tempo, [(tick, note), ...])`` from a MIDI file."""
    src = mido.MidiFile(path)
    tempo, notes = mido.bpm2tempo(128), []
    for track in src.tracks:
        t = 0
        for m in track:
            t += m.time
            if m.type == "set_tempo":
                tempo = m.tempo
            elif m.type == "note_on" and m.velocity > 0:
                notes.append((t, m.note))
    return src.ticks_per_beat, tempo, notes


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bass_midi")
    ap.add_argument("out")
    a = ap.parse_args(argv)
    tpb, tempo, notes = read_bass(a.bass_midi)
    roots = bar_roots(notes, tpb * 4)
    ev = build_events(roots, tpb)
    write_midi(a.out, ev, track_name="S-1 with P-6", tempo=tempo, ticks_per_beat=tpb)
    n = sum(1 for _, m in ev if m.type == "note_on")
    print(f"{a.out}: {len(roots)} bars, {round(mido.tempo2bpm(tempo))} BPM, {n} notes")


if __name__ == "__main__":
    main()
