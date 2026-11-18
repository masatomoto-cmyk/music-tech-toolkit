"""Parse the time-stamped MIDI logs written by :mod:`musictk.midi.spy`.

Each log line looks like ``  12.345 note_on channel=11 note=36 velocity=100 | 9b 24 64``:
elapsed seconds, a human readable message, a ``|`` and the raw bytes in hex.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

import mido


def message_kind(msg: mido.Message) -> str:
    """Group note_on / note_off under ``note``; everything else keeps its type."""
    return "note" if msg.type in ("note_on", "note_off") else msg.type


def parse_log(
    lines: Iterable[str],
    *,
    only: set[str] | None = None,
    skip: set[str] | None = None,
    t_from: float = 0.0,
    t_to: float = float("inf"),
) -> list[tuple[float, mido.Message]]:
    """Return ``(seconds, message)`` pairs from log lines, filtered by kind and time."""
    skip = skip or set()
    out: list[tuple[float, mido.Message]] = []
    for line in lines:
        if "|" not in line:
            continue
        left, raw = line.rsplit("|", 1)
        t = float(left.split()[0])
        if not t_from <= t <= t_to:
            continue
        msg = mido.Message.from_hex(raw.strip())
        kind = message_kind(msg)
        if (only and kind not in only) or kind in skip:
            continue
        out.append((t, msg))
    return out


def summarize(messages: Iterable[tuple[float, mido.Message]]) -> Counter:
    """Count messages by type."""
    return Counter(m.type for _, m in messages)
