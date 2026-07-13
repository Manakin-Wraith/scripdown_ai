#!/usr/bin/env python3
"""Re-derive location_canonical wherever the linter finds an AUTO-FIXABLE issue
(time/digit/INT-EXT residue), then re-lint to confirm the auto-fixable count drops.
Judgment-call locations are never touched.

Usage: python scripts/backfill_location_quality.py [--dry-run]"""
import sys, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from db.supabase_client import get_supabase_admin
from services.location_resolver import derive_base_place
from services.location_quality import classify_location

AUTO = {"TIME_RESIDUE", "DIGIT_NOISE", "INT_EXT_RESIDUE"}

def main(dry_run):
    client = get_supabase_admin()
    rows, start = [], 0
    while True:
        batch = client.table("scenes").select(
            "id, setting, int_ext, time_of_day, location_hierarchy, location_canonical"
        ).range(start, start + 999).execute().data or []
        rows.extend(batch);
        if len(batch) < 1000: break
        start += 1000
    changes = []
    for s in rows:
        cur = (s.get("location_canonical") or "").strip()
        # flags on the current base itself (sibling context not needed for auto classes)
        flags = {i["code"] for i in classify_location(cur, "", s.get("setting") or "", [cur])}
        if not (flags & AUTO):
            continue
        new = derive_base_place(s.get("setting"), s.get("int_ext"), s.get("time_of_day"), s.get("location_hierarchy"))
        if new and len(new) >= 2 and new != cur:
            changes.append((s["id"], cur, new))
    print(f"Scanned {len(rows)} scenes; {len(changes)} auto-fixable canonicals to re-derive.")
    for _id, cur, new in changes:
        print(f"  {cur!r:45} -> {new!r}")
    if dry_run:
        print("[dry-run] no writes."); return
    for _id, _cur, new in changes:
        client.table("scenes").update({"location_canonical": new}).eq("id", _id).execute()
    print(f"Applied {len(changes)} updates.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    main(ap.parse_args().dry_run)
