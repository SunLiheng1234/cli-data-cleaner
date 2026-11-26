import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cleaner"))

from rules import is_missing, fill_missing, dedup, validate


def test_missing_variants():
    for v in ["N/A", " null ", "None", "NA", "-", "?", "", None]:
        assert is_missing(v), v
    assert not is_missing("0")
    assert not is_missing("nan123")


def test_fill_drop():
    rows = [{"v": "1"}, {"v": "N/A"}, {"v": "2"}]
    out = fill_missing(rows, "v", "drop")
    assert [r["v"] for r in out] == ["1", "2"]


def test_fill_constant():
    rows = [{"v": ""}, {"v": "2"}]
    out = fill_missing(rows, "v", "constant", "0")
    assert out[0]["v"] == "0"


def test_fill_mean():
    rows = [{"v": "2"}, {"v": ""}, {"v": "4"}]
    out = fill_missing(rows, "v", "mean")
    assert out[1]["v"] == "3"


def test_fill_mean_all_missing():
    rows = [{"v": "N/A"}, {"v": ""}]
    out = fill_missing(rows, "v", "mean")
    assert all(r["v"] == "0" for r in out)


def test_fill_mean_non_numeric_raises():
    import pytest
    with pytest.raises(ValueError):
        fill_missing([{"v": "abc"}], "v", "mean")


def test_dedup_full_row():
    rows = [{"a": "1", "b": "x"}, {"a": "1", "b": "x"}, {"a": "2", "b": "y"}]
    assert len(dedup(rows)) == 2


def test_dedup_keys_and_normalize():
    rows = [{"a": "X "}, {"a": "x"}, {"a": "y"}]
    assert len(dedup(rows, ["a"])) == 3
    assert len(dedup(rows, ["a"], normalize=True)) == 2


def test_dedup_missing_key_raises():
    import pytest
    with pytest.raises(KeyError):
        dedup([{"a": "1"}], ["b"])


def test_validate_int():
    rows = [{"v": "1"}, {"v": "-3"}, {"v": "3.0"}, {"v": "x"}]
    bad = validate(rows, "v", {"type": "int"})
    assert [b[0] for b in bad] == [2, 3]


def test_validate_float_sci():
    rows = [{"v": "1e3"}, {"v": "abc"}]
    bad = validate(rows, "v", {"type": "float"})
    assert len(bad) == 1 and bad[0][0] == 1


def test_validate_date_leap():
    assert validate([{"d": "2020-02-29"}], "d", {"type": "date"}) == []
    assert validate([{"d": "2021-02-29"}], "d", {"type": "date"}) != []


def test_validate_empty_is_missing_not_illegal():
    assert validate([{"v": ""}, {"v": "N/A"}], "v", {"type": "int"}) == []


def test_validate_regex_and_enum():
    email = {"type": "regex", "pattern": r"^[^@]+@[^@]+\.[^@]+$"}
    assert validate([{"e": "a@x.com"}, {"e": "bad"}], "e", email)[0][0] == 1
    enum = {"type": "enum", "allowed": ["a", "b"]}
    assert validate([{"c": "a"}, {"c": "z"}], "c", enum)[0][0] == 1