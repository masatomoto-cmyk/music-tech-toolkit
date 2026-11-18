"""Helpers shared by the Roland S-1 MIDI-file generators."""
from __future__ import annotations

import mido

# S-1 receives on MIDI channel 12 (0-based 11).
S1_CHANNEL = 11
CC_RESONANCE = 71
CC_CUTOFF = 74

# Within a bar: which 16th-note steps get an accent.
ACCENT_STEPS = frozenset({0, 3, 7, 10, 14})

# Same-tick ordering: release the old note, move the knobs, then play the new note.
_ORDER = {"note_off": 0, "control_change": 1, "note_on": 2}


def write_midi(
    path: str,
    events: list[tuple[int, mido.Message]],
    *,
    track_name: str,
    tempo: int,
    ticks_per_beat: int,
) -> mido.MidiFile:
    """Write absolute-tick ``events`` to a one-track MIDI file and return it."""
    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage("track_name", name=track_name, time=0))
    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
    track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    now = 0
    for t, msg in sorted(events, key=lambda e: (e[0], _ORDER[e[1].type])):
        track.append(msg.copy(time=t - now))
        now = t
    track.append(mido.MetaMessage("end_of_track", time=0))
    mid.save(path)
    return mid
