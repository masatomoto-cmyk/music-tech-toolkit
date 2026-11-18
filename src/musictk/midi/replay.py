"""Replay a log written by :mod:`musictk.midi.spy` to a MIDI output with the original timing.

    python -m musictk.midi.replay session.log --only note,control_change --from 10 --to 40
    python -m musictk.midi.replay session.log --dry      # just count messages
"""
from __future__ import annotations

import argparse
import sys
import time

import mido

from .log import parse_log, summarize


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("log")
    ap.add_argument("--only", help="comma separated kinds to keep (note, control_change, ...)")
    ap.add_argument("--skip", help="comma separated kinds to drop")
    ap.add_argument("--from", dest="t_from", type=float, default=0.0)
    ap.add_argument("--to", dest="t_to", type=float, default=float("inf"))
    ap.add_argument("--port", default="S-1 MIDI IN")
    ap.add_argument("--dry", action="store_true")
    return ap


def main(argv: list[str] | None = None) -> None:
    a = build_parser().parse_args(argv)
    with open(a.log) as f:
        msgs = parse_log(
            f,
            only=set(a.only.split(",")) if a.only else None,
            skip=set(a.skip.split(",")) if a.skip else None,
            t_from=a.t_from,
            t_to=a.t_to,
        )
    print(f"{len(msgs)} messages:", dict(summarize(msgs)))
    if a.dry or not msgs:
        sys.exit(0)
    with mido.open_output(a.port) as out:
        start, first = time.time(), msgs[0][0]
        for t, m in msgs:
            wait = (t - first) - (time.time() - start)
            if wait > 0:
                time.sleep(wait)
            out.send(m)


if __name__ == "__main__":
    main()
