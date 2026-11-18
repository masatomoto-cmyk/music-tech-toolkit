import mido

from musictk.midi.log import parse_log, summarize
from musictk.midi.spy import format_line

NOTE_ON = mido.Message("note_on", channel=11, note=36, velocity=100)
CC = mido.Message("control_change", channel=11, control=74, value=40)


def lines():
    return [
        "ready",
        format_line(1.0, NOTE_ON),
        format_line(2.5, CC),
        format_line(9.0, NOTE_ON.copy(velocity=0)),
    ]


def test_roundtrip_through_log_format():
    msgs = parse_log(lines())
    assert [m for _, m in msgs][0] == NOTE_ON
    assert [t for t, _ in msgs] == [1.0, 2.5, 9.0]


def test_filters():
    assert len(parse_log(lines(), only={"note"})) == 2
    assert len(parse_log(lines(), skip={"note"})) == 1
    assert [t for t, _ in parse_log(lines(), t_from=2, t_to=5)] == [2.5]


def test_summarize():
    assert summarize(parse_log(lines())) == {"note_on": 2, "control_change": 1}
