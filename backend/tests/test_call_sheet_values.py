import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.call_sheet_values as v


def test_normalize_time_trims_seconds():
    assert v.normalize_time("06:30:00") == "06:30"
    assert v.normalize_time("06:30") == "06:30"


def test_normalize_time_empty_is_none():
    assert v.normalize_time("") is None
    assert v.normalize_time(None) is None


@pytest.mark.parametrize("bad", ["6:30", "25:00", "06:60", "noon", 630])
def test_normalize_time_rejects(bad):
    with pytest.raises(ValueError):
        v.normalize_time(bad)


def test_validate_text_and_length():
    assert v.validate_value("text", "hi") == "hi"
    with pytest.raises(ValueError):
        v.validate_value("text", "x" * 2001)
    with pytest.raises(ValueError):
        v.validate_value("text", 5)
    assert len(v.validate_value("textarea", "x" * 10000)) == 10000


def test_validate_number():
    assert v.validate_value("number", 5) == 5
    assert v.validate_value("number", "7") == 7
    assert v.validate_value("number", "7.5") == 7.5
    assert v.validate_value("number", "") is None
    with pytest.raises(ValueError):
        v.validate_value("number", True)
    with pytest.raises(ValueError):
        v.validate_value("number", "abc")


def test_validate_link():
    assert v.validate_value("link", "https://maps.app.goo.gl/x") == "https://maps.app.goo.gl/x"
    with pytest.raises(ValueError):
        v.validate_value("link", "javascript:alert(1)")
    with pytest.raises(ValueError):
        v.validate_value("link", "ftp://x.com")


def test_validate_count():
    assert v.validate_value("count", 0) == 0
    with pytest.raises(ValueError):
        v.validate_value("count", -1)
    with pytest.raises(ValueError):
        v.validate_value("count", "3")


def test_none_always_means_clear():
    for t in ("text", "time", "number", "link", "count", "textarea"):
        assert v.validate_value(t, None) is None


def test_merge_values_touches_only_sent_keys():
    merged, ignored = v.merge_values({"a": "1", "b": "2"}, {"a": "9"}, {"a": "text", "b": "text"})
    assert merged == {"a": "9", "b": "2"} and ignored == []


def test_merge_values_null_clears_and_unknown_ignored():
    merged, ignored = v.merge_values({"a": "1", "b": "2"}, {"a": None, "zzz": "x"}, {"a": "text", "b": "text"})
    assert merged == {"b": "2"} and ignored == ["zzz"]


def test_merge_values_error_names_key():
    with pytest.raises(ValueError, match="link"):
        v.merge_values({}, {"link": "nope"}, {"link": "link"})


def test_merge_values_keeps_values_for_keys_not_in_types():
    # a field removed from the template keeps its stored value
    merged, _ = v.merge_values({"old": "keep"}, {"a": "1"}, {"a": "text"})
    assert merged == {"old": "keep", "a": "1"}


def test_merge_nested():
    merged, ignored = v.merge_nested(
        {"s1": {"a": "1"}}, {"s1": {"b": "2"}, "s2": {"a": "x"}, "zzz": {"a": "y"}},
        {"s1", "s2"}, {"a": "text", "b": "text"})
    assert merged == {"s1": {"a": "1", "b": "2"}, "s2": {"a": "x"}}
    assert ignored == ["zzz"]


def test_merge_nested_drops_empty_inner():
    merged, _ = v.merge_nested({"s1": {"a": "1"}}, {"s1": {"a": None}}, {"s1"}, {"a": "text"})
    assert merged == {}


def test_catering_defaults_split_background_from_cast():
    crew = [{}, {}, {}]
    cast = [{"casting": {"tier": "lead"}}, {"casting": {"tier": "background"}}]
    d = v.catering_defaults(crew, cast)
    assert d["lunch"] == {"crew": 3, "cast": 1, "add_crew": 0, "extras": 1}
    assert set(d) == set(v.MEALS)


def test_effective_catering_overrides_only_known():
    d = v.catering_defaults([{}], [])
    eff = v.effective_catering(d, {"lunch": {"crew": 9, "bogus": 1}, "brunch": {"crew": 1}})
    assert eff["lunch"]["crew"] == 9 and "bogus" not in eff["lunch"]
    assert eff["craft"]["crew"] == 1
