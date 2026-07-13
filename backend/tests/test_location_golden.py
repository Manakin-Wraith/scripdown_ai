import json
from pathlib import Path

from services.location_resolver import derive_base_place, derive_sub_place
from services.location_quality import classify_location

CASES = json.loads((Path(__file__).parent / "fixtures" / "location_golden.json").read_text())


def test_golden_corpus():
    failures = []
    for c in CASES:
        base = derive_base_place(c["setting"], c["int_ext"], c["time_of_day"], c["location_hierarchy"])
        sub = derive_sub_place(c["setting"], c["int_ext"], c["time_of_day"], c["location_hierarchy"])
        flags = {i["code"] for i in classify_location(base, sub, c["setting"], [base])}
        exp = c["expect"]
        if base != exp["base"] or sub != exp["sub"] or flags != set(exp["flags"]):
            failures.append(f"{c['setting']!r}: got ({base!r},{sub!r},{sorted(flags)}) "
                            f"expected ({exp['base']!r},{exp['sub']!r},{exp['flags']})")
    assert not failures, "\n".join(failures)
