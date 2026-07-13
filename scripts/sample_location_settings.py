#!/usr/bin/env python3
"""Sample distinct real scene settings and print proposed golden-corpus rows.
Human curates the output into backend/tests/fixtures/location_golden.json."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from db.supabase_client import get_supabase_admin
from services.location_resolver import derive_base_place, derive_sub_place
from services.location_quality import classify_location

def main(limit=60):
    client = get_supabase_admin()
    rows, start = [], 0
    while True:
        batch = client.table("scenes").select(
            "setting, int_ext, time_of_day, location_hierarchy").range(start, start + 999).execute().data or []
        rows.extend(batch)
        if len(batch) < 1000:
            break
        start += 1000
    seen, out = set(), []
    for s in rows:
        key = (s.get("setting") or "").strip().upper()
        if not key or key in seen:
            continue
        seen.add(key)
        base = derive_base_place(s.get("setting"), s.get("int_ext"), s.get("time_of_day"), s.get("location_hierarchy"))
        sub = derive_sub_place(s.get("setting"), s.get("int_ext"), s.get("time_of_day"), s.get("location_hierarchy"))
        flags = sorted({i["code"] for i in classify_location(base, sub, s.get("setting") or "", [base])})
        if flags:  # only surface still-flagged ones for review
            out.append({"setting": s.get("setting"), "int_ext": s.get("int_ext"),
                        "time_of_day": s.get("time_of_day"), "location_hierarchy": s.get("location_hierarchy") or [],
                        "expect": {"base": base, "sub": sub, "flags": flags}})
        if len(out) >= limit:
            break
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
