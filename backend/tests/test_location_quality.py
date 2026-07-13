from services.location_quality import classify_location, lint_script_locations


def codes(issues):
    return {i["code"] for i in issues}


def test_time_residue_flagged_autofixable():
    issues = classify_location("OFFICE", "EARLY MORNING", "SHELTER. OFFICE. EARLY MORNING.", ["OFFICE"])
    assert "TIME_RESIDUE" in codes(issues)
    assert all(i["auto_fixable"] for i in issues if i["code"] == "TIME_RESIDUE")


def test_digit_noise_flagged():
    assert "DIGIT_NOISE" in codes(classify_location("KITCHEN", "2 7", "HOME. KITCHEN. 2 7", ["KITCHEN"]))
    assert "DIGIT_NOISE" in codes(classify_location("STREETS", "3 A", "CITY STREETS. 3 A", ["STREETS"]))


def test_int_ext_residue_flagged():
    assert "INT_EXT_RESIDUE" in codes(classify_location("/EXT", "", "/EXT. COCKPIT", ["/EXT"]))


def test_description_bleed_flagged_not_autofixable():
    issues = classify_location("CAMERA DOLLIES DOWN A CORRIDOR AS PRISON", "", "INT. CELLBLOCK", ["CELLBLOCK"])
    assert "DESCRIPTION_BLEED" in codes(issues)
    assert all(not i["auto_fixable"] for i in issues if i["code"] == "DESCRIPTION_BLEED")


def test_possible_parent_suggests_shorter_base():
    issues = classify_location("HOMELESS SHELTER WORKSHOP", "", "INT. HOMELESS SHELTER WORKSHOP",
                               ["HOMELESS SHELTER", "HOMELESS SHELTER WORKSHOP"])
    pp = [i for i in issues if i["code"] == "POSSIBLE_PARENT"]
    assert pp and pp[0]["suggestion"] == "HOMELESS SHELTER"


def test_near_duplicate_flagged():
    issues = classify_location("CHAPMANS PEAK", "", "EXT. CHAPMANS PEAK",
                               ["CHAPMANS PEAK", "CHAPMAN'S PEAK"])
    assert "NEAR_DUPLICATE" in codes(issues)


def test_clean_locations_have_no_flags():
    for b in ["MRS. JONES' HOUSE", "C-MAX PRISON", "GARAGE / BACKROOM", "INTERSTATE 5"]:
        assert classify_location(b, "", f"INT. {b} - DAY", [b]) == [], b


def test_none_sibling_bases_does_not_raise():
    result = classify_location("OFFICE", "", "INT. OFFICE", None)
    assert result == []


def test_distinct_digit_noise_segments_both_reported():
    issues = classify_location("2 7", "3 4", "HOME. 2 7. 3 4", ["2 7"])
    digit = [i for i in issues if i["code"] == "DIGIT_NOISE"]
    assert len(digit) == 2
    assert digit[0]["message"] != digit[1]["message"]


def test_lint_script_shape():
    scenes = [
        {"setting": "INT. OPULENT SANDTON HOME. BEDROOM. DAY.", "int_ext": "INT",
         "time_of_day": "DAY", "location_hierarchy": [], "location_canonical": "OPULENT SANDTON HOME",
         "is_omitted": False},
    ]
    report = lint_script_locations(scenes)
    assert "total" in report and "by_key" in report
    assert isinstance(report["total"], int)
