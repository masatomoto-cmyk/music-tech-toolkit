import mido

from musictk.daw import logic_house
from musictk.hardware import bassline, jam, phrase


def test_house_short_form_is_32_bars_with_four_parts():
    mid, total, markers = logic_house.build("A", 122, "deep", 1, "short")
    assert total == 32
    assert [name for name, _ in markers] == ["Intro", "Groove", "Break", "Drop"]
    names = {m.name for tr in mid.tracks for m in tr if m.type == "track_name"}
    assert {"Drums", "Bass", "Chords", "Lead"} <= names


def test_house_is_deterministic_per_seed():
    a, _, _ = logic_house.build("A", 122, "deep", 7, "short")
    b, _, _ = logic_house.build("A", 122, "deep", 7, "short")
    c, _, _ = logic_house.build("A", 122, "deep", 8, "short")
    dump = lambda mid: [tuple(m.dict().items()) for tr in mid.tracks for m in tr]  # noqa: E731
    assert dump(a) == dump(b)
    assert dump(a) != dump(c)


def test_bassline_events_stay_on_s1_channel_and_in_range(tmp_path):
    events = bassline.build_events(bars=8, key="C", seed=1)
    for _, m in events:
        assert m.channel == 11
        if m.type == "control_change":
            assert 0 <= m.value <= 127
    out = tmp_path / "bass.mid"
    bassline.main([str(out), "--bars", "4"])
    assert mido.MidiFile(str(out)).length > 0


def test_cutoff_sweeps_open_then_back():
    assert bassline.cutoff_at(0, 64) == 30
    assert bassline.cutoff_at(48, 64) == 100
    assert bassline.cutoff_at(63, 64) < 50
    assert jam.cutoff_at(0, 64) == 30


def test_jam_octave_jump_only_in_last_bar():
    assert jam.note_for(2, 64) == jam.PATTERN[2]
    assert jam.note_for(50, 64) == jam.PATTERN[50 % 16] + 12


def test_phrase_follows_bass_roots(tmp_path):
    tpb = 480
    bar = tpb * 4
    notes = [(0, 36), (bar, 44), (3 * bar, 36)]  # bar 2 is silent
    roots = phrase.bar_roots(notes, bar)
    assert roots == [36, 44, None, 36]
    sections = [(1, 4, "A", 40, 80, 60)]
    ev = phrase.build_events(roots, tpb, sections)
    played = {t // bar for t, m in ev if m.type == "note_on"}
    assert 2 not in played and {0, 1, 3} <= played


def test_phrase_chord_shift_and_hold_length():
    assert phrase.chord_shift(0, 3) == 3          # C stays minor
    assert phrase.chord_shift(44, 3) == 4         # Ab bar: major third
    assert phrase.hold_length(phrase.RIFF["hold"], 0) == 8
    assert phrase.hold_length(phrase.RIFF["A"], 0) == 1
