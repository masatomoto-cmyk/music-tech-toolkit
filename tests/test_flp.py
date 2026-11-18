import struct

import pytest

from musictk.daw import flp


def build_flp(events: bytes, ppq: int = 96) -> bytes:
    header = b"FLhd" + struct.pack("<I", 6) + struct.pack("<hHH", 0, 1, ppq)
    return header + b"FLdt" + struct.pack("<I", len(events)) + events


def test_parses_all_four_payload_sizes():
    name = "Kick".encode("utf-16le") + b"\x00\x00"
    events = (
        bytes([10, 7])                                  # 1-byte payload
        + bytes([66]) + struct.pack("<H", 300)          # 2-byte payload
        + bytes([130]) + struct.pack("<I", 70000)       # 4-byte payload
        + bytes([203, len(name)]) + name                # variable length text
    )
    ppq, ev = flp.parse(build_flp(events, ppq=96))
    assert ppq == 96
    assert ev[:3] == [(10, 7), (66, 300), (130, 70000)]
    assert flp.text(ev[3][1]) == "Kick"


def test_variable_length_prefix_over_127_bytes():
    blob = b"x" * 200
    prefix = bytes([200 & 0x7F | 0x80, 200 >> 7])
    _, ev = flp.parse(build_flp(bytes([200]) + prefix + blob))
    assert ev == [(200, blob)]


def test_rejects_non_flp():
    with pytest.raises(flp.FlpError):
        flp.parse(b"RIFF....")
