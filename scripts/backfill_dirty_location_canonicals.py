#!/usr/bin/env python3
"""
Backfill: clean dirty location_canonical values.

Some legacy scenes carry a location_canonical that is a full slugline rather than
a clean base place — trailing time-of-day, leading INT./EXT., comma sub-areas
("TK'S HOUSE, KITCHEN"), or period-delimited sluglines ("OPULENT SANDTON HOME.
BEDROOM. DAY"). These show as messy "locations" and don't group.

This recomputes location_canonical using the resolver's derive_base_place (now
comma- and spaced-dash aware) plus a guarded period-slugline cleanup, ONLY for
scenes whose current canonical looks dirty. Clean canonicals and properly-nested
scenes (canonical already = base) are left untouched.

Usage:
    python scripts/backfill_dirty_location_canonicals.py --dry-run   # preview
    python scripts/backfill_dirty_location_canonicals.py             # apply
"""

import sys
import re
import argparse
from pathlib import Path

backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

import json
from db.supabase_client import get_supabase_admin
from services.location_resolver import normalize_place, _INT_EXT_PREFIX, INT_EXT_TOKENS

TIME_WORDS = {
    'DAY', 'NIGHT', 'DUSK', 'DAWN', 'MORNING', 'EVENING', 'AFTERNOON',
    'CONTINUOUS', 'LATER', 'SAME', 'MAGIC HOUR', 'EARLY', 'PRESENT DAY',
    'EARLY MORNING', 'NIGHT/EARLY MORNING', 'THE PRESENT',
}
# Words that end in a period but are abbreviations, not slugline separators.
ABBREV = {'MR', 'MRS', 'MS', 'DR', 'ST', 'MT', 'PROF', 'SGT', 'DET', 'REV', 'LT', 'CAPT', 'GEN'}

_DIRTY = re.compile(
    r",|\s+[-–—]\s+|^[/ ]*(INT|EXT|INT/EXT|I/E)\b|\.\s+\S|"
    r"[ .](DAY|NIGHT|DUSK|DAWN|MORNING|EVENING|AFTERNOON|CONTINUOUS|LATER|SAME|"
    r"MAGIC HOUR|EARLY|PRESENT|EARLY MORNING)\.?\s*$",
    re.IGNORECASE,
)


def _strip_trailing_time(s: str) -> str:
    prev = None
    while prev != s:
        prev = s
        s = re.sub(
            r"[ .]+(" + "|".join(re.escape(w) for w in TIME_WORDS) + r")\.?\s*$",
            "", s, flags=re.IGNORECASE,
        ).strip(" .,-")
    return s


def _raw_source(hierarchy, setting):
    if hierarchy:
        h = hierarchy
        if isinstance(h, str):
            try:
                h = json.loads(h)
            except (ValueError, TypeError):
                h = []
        if h:
            return str(h[0])
    return setting or ''


def clean_canonical(setting, int_ext, time_of_day, hierarchy):
    """Best clean base place for a dirty scene. Strips INT/EXT (incl. a leading
    slash), splits on comma / spaced-dash / spaced-slash dropping INT-EXT and time
    tokens, then guard-splits any remaining period slugline (protecting MRS. etc.)."""
    raw = _INT_EXT_PREFIX.sub("", _raw_source(hierarchy, setting)).strip()
    parts = [p.strip() for p in re.split(r"\s*,\s*|\s+[-–—]\s+|\s+/\s+", raw) if p.strip()]
    parts = [
        p for p in parts
        if normalize_place(_INT_EXT_PREFIX.sub("", p)) not in INT_EXT_TOKENS
        and p.rstrip('.').upper() not in TIME_WORDS
    ]
    base = parts[0] if parts else raw
    # Guarded period-slugline split: "OPULENT SANDTON HOME. BEDROOM. DAY" -> base.
    if '. ' in base:
        segs = [p.strip() for p in base.split('. ') if p.strip()]
        if segs and segs[0].rstrip('.').upper() not in ABBREV and len(segs[0]) > 2:
            base = segs[0]
    return normalize_place(_strip_trailing_time(_INT_EXT_PREFIX.sub("", base)))


def main(dry_run: bool):
    client = get_supabase_admin()
    rows, start, page = [], 0, 1000
    while True:
        res = client.table('scenes').select(
            'id, setting, int_ext, time_of_day, location_hierarchy, location_canonical'
        ).range(start, start + page - 1).execute()
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < page:
            break
        start += page

    changes = []
    for s in rows:
        cur = (s.get('location_canonical') or '').strip()
        if not cur or not _DIRTY.search(cur):
            continue
        new = clean_canonical(
            s.get('setting'), s.get('int_ext'), s.get('time_of_day'), s.get('location_hierarchy')
        )
        if new and len(new) >= 2 and new != cur:
            changes.append((s['id'], cur, new))

    print(f"Scanned {len(rows)} scenes; {len(changes)} dirty canonicals to clean.\n")
    for _id, cur, new in changes:
        print(f"  {cur!r:55} ->  {new!r}")

    if dry_run:
        print("\n[dry-run] no changes written.")
        return
    for _id, _cur, new in changes:
        client.table('scenes').update({'location_canonical': new}).eq('id', _id).execute()
    print(f"\nApplied {len(changes)} updates.")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    main(ap.parse_args().dry_run)
