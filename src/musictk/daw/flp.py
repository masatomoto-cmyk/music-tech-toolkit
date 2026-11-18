"""Minimal reader for FL Studio project (.flp) files.

An .flp file is the ``FLhd`` header followed by an ``FLdt`` chunk of events. Each event is a
one-byte id plus a payload whose size depends on the id range:

    0-63    1 byte          64-127   2 bytes (little endian)
    128-191 4 bytes         192-255  variable length (7-bit length prefix)
"""
from __future__ import annotations

import struct


class FlpError(ValueError):
    pass


def parse(data: bytes) -> tuple[int, list[tuple[int, int | bytes]]]:
    """Return ``(ppq, events)`` for the bytes of an .flp file."""
    if data[:4] != b"FLhd":
        raise FlpError("not an FL Studio project (missing FLhd header)")
    _fmt, _channels, ppq = struct.unpack("<hHH", data[8:14])
    i = 14
    if data[i:i + 4] != b"FLdt":
        raise FlpError("missing FLdt data chunk")
    i += 8
    events: list[tuple[int, int | bytes]] = []
    while i < len(data):
        eid = data[i]
        i += 1
        if eid < 64:
            payload: int | bytes = data[i]
            i += 1
        elif eid < 128:
            payload = struct.unpack("<H", data[i:i + 2])[0]
            i += 2
        elif eid < 192:
            payload = struct.unpack("<I", data[i:i + 4])[0]
            i += 4
        else:
            size = shift = 0
            while True:
                byte = data[i]
                i += 1
                size |= (byte & 0x7F) << shift
                shift += 7
                if not byte & 0x80:
                    break
            payload = data[i:i + size]
            i += size
        events.append((eid, payload))
    return ppq, events


def events(path: str) -> tuple[int, list[tuple[int, int | bytes]]]:
    with open(path, "rb") as f:
        return parse(f.read())


def text(payload: bytes) -> str:
    """Decode a text event (UTF-16LE in recent FL versions, Latin-1 in old ones)."""
    try:
        return payload.decode("utf-16le").rstrip("\x00")
    except UnicodeDecodeError:
        return payload.decode("latin1").rstrip("\x00")
