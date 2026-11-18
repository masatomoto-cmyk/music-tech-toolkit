from musictk.research.subtitles import json3_to_lines, vtt_to_lines

VTT = """WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:03.000
hello <c>world</c>

00:01:05.000 --> 00:01:07.000
hello world
second line

00:01:09.000 --> 00:01:10.000
second line
"""


def test_vtt_strips_tags_and_rolling_duplicates():
    assert vtt_to_lines(VTT.splitlines()) == ["[0:01] hello world", "[1:05] second line"]


def test_json3():
    data = {"events": [{"tStartMs": 65000, "segs": [{"utf8": "a "}, {"utf8": "b"}]}, {"tStartMs": 0, "segs": []}]}
    assert json3_to_lines(data) == ["[1:05] a b"]
