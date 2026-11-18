"""Turn YouTube subtitle files (WebVTT or json3) into plain ``[m:ss] text`` lines.

Useful for feeding talks and tutorials into a summariser or a notebook tool.
Only handles subtitle files you have the right to use (e.g. your own downloads).
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable

_CUE = re.compile(r"(\d\d):(\d\d):(\d\d)\.\d+ -->")
_TAG = re.compile(r"<[^>]+>")
_HEADERS = ("WEBVTT", "Kind:", "Language:")


def vtt_to_lines(lines: Iterable[str]) -> list[str]:
    """Convert WebVTT lines; drops tags, headers and the repeated lines of rolling captions."""
    cues: list[tuple[str, str]] = []
    stamp, prev = "", None
    for raw in lines:
        line = raw.strip()
        m = _CUE.match(line)
        if m:
            stamp = f"{int(m[1]) * 60 + int(m[2])}:{m[3]}"
            continue
        if not line or line.startswith(_HEADERS):
            continue
        text = _TAG.sub("", line)
        if text and text != prev:
            cues.append((stamp, text))
            prev = text
    seen: set[str] = set()
    out: list[str] = []
    for stamp, text in cues:
        if text in seen:
            continue
        seen.add(text)
        out.append(f"[{stamp}] {text}")
    return out


def json3_to_lines(data: dict) -> list[str]:
    """Convert YouTube's json3 caption format."""
    out: list[str] = []
    for ev in data.get("events", []):
        text = "".join(seg.get("utf8", "") for seg in ev.get("segs", [])).strip()
        if text:
            sec = ev.get("tStartMs", 0) // 1000
            out.append(f"[{sec // 60}:{sec % 60:02d}] {text}")
    return out


def main(argv: list[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src", help=".vtt or .json3 file")
    ap.add_argument("dst", help="output .txt")
    a = ap.parse_args(argv)
    if a.src.endswith(".vtt"):
        with open(a.src, encoding="utf-8") as f:
            lines = vtt_to_lines(f)
    else:
        with open(a.src, encoding="utf-8") as f:
            lines = json3_to_lines(json.load(f))
    with open(a.dst, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
