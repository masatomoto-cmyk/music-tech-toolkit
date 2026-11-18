import pytest

from musictk.hardware import s1


@pytest.mark.parametrize(
    "name,expected",
    [("C4", 60), ("A4", 69), ("F#3", 54), ("Bb2", 46), ("c-1", 0), ("60", 60)],
)
def test_note_num(name, expected):
    assert s1.note_num(name) == expected


def test_note_num_rejects_garbage():
    with pytest.raises(SystemExit):
        s1.note_num("H9")


def test_resolve_by_name_and_number():
    assert s1.resolve("cutoff") == 74
    assert s1.resolve("RESO") == 71
    assert s1.resolve("74") == 74
    with pytest.raises(SystemExit):
        s1.resolve("nope")


def test_param_table_is_valid_cc_numbers():
    ccs = [v[0] for v in s1.PARAMS.values()]
    assert all(0 <= c <= 127 for c in ccs)
    assert len(ccs) == len(set(ccs)), "two names share one CC number"


def test_find_port():
    assert s1.find_port(["IAC Bus 1", "S-1 MIDI IN"], "S-1") == "S-1 MIDI IN"
    with pytest.raises(SystemExit):
        s1.find_port(["IAC Bus 1"], "S-1")
