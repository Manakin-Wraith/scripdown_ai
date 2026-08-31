import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.crew_import import parse_crew_csv

CODES = {"camera", "grip"}
NAMES = {"camera": "Camera", "grip": "Grip"}


def _parse(text):
    return parse_crew_csv(text, CODES, NAMES)


def test_missing_name_column_is_fatal():
    out = _parse("email,role\na@b.com,Gaffer\n")
    assert out["fatal"] is not None
    assert out["rows"] == []


def test_header_normalization_and_extra_columns():
    out = _parse("  Name , Company Name ,Nonsense\nGary,Acme Lighting,ignore\n")
    assert out["fatal"] is None
    assert out["rows"][0]["name"] == "Gary"
    assert out["rows"][0]["company_name"] == "Acme Lighting"


def test_blank_name_row_skipped_with_line_number():
    out = _parse("name,role\n,Gaffer\nGary,Best Boy\n")
    assert [r["name"] for r in out["rows"]] == ["Gary"]
    assert out["errors"] == [{"line": 2, "reason": "missing name"}]


def test_non_numeric_rate_skips_row():
    out = _parse("name,rate\nGary,lots\n")
    assert out["rows"] == []
    assert out["errors"][0]["line"] == 2
    assert "rate" in out["errors"][0]["reason"].lower()


def test_bad_rate_unit_coerced_with_warning():
    out = _parse("name,rate_unit\nGary,hour\n")
    assert out["rows"][0]["rate_unit"] is None
    assert out["errors"][0]["reason"].lower().startswith("rate_unit")


def test_department_matched_by_code_or_name():
    out = _parse("name,department\nGary,camera\nAmy,Grip\n")
    assert [r["department_code"] for r in out["rows"]] == ["camera", "grip"]


def test_unknown_department_skips_row():
    out = _parse("name,department\nGary,wizardry\n")
    assert out["rows"] == []
    assert "department" in out["errors"][0]["reason"].lower()
