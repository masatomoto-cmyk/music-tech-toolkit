"""Create a virtual MIDI input ("S-1 Spy") and log whatever arrives, with timestamps.

Point a DAW's MIDI output at the virtual port, then replay the log with
``python -m musictk.midi.replay``.

    python -m musictk.midi.spy session.log
"""
from __future__ import annotations

import argparse
import time

import mido


def format_line(elapsed: float, msg: mido.Message) -> str:
    return f"{elapsed:8.3f} {msg} | {msg.hex()}"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("log", help="file to append to")
    ap.add_argument("--name", default="S-1 Spy", help="virtual port name")
    args = ap.parse_args(argv)

    t0 = time.time()
    with open(args.log, "a", buffering=1) as log, mido.open_input(args.name, virtual=True) as port:
        log.write("ready\n")
        for msg in port:
            log.write(format_line(time.time() - t0, msg) + "\n")


if __name__ == "__main__":
    main()
