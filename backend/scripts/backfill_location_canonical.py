"""
Backfill scenes.location_canonical for all existing scenes.

Idempotent — re-deriving is deterministic. Applies any existing
location_aliases so previously-merged places stay canonical.

Usage (from backend/):  python scripts/backfill_location_canonical.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db.supabase_client import get_supabase_admin  # service-role client (bypasses RLS)
from services.location_resolver import derive_base_place, normalize_place


def main():
    supabase = get_supabase_admin()

    # Preload alias maps per script: {script_id: {alias_place: canonical_place}}
    aliases = supabase.table('location_aliases').select(
        'script_id, alias_place, canonical_place'
    ).execute().data or []
    alias_by_script = {}
    for row in aliases:
        alias_by_script.setdefault(row['script_id'], {})[row['alias_place']] = row['canonical_place']

    # Page through scenes
    page, size, updated = 0, 500, 0
    while True:
        rows = supabase.table('scenes').select(
            'id, script_id, setting, int_ext, time_of_day, location_hierarchy'
        ).range(page * size, page * size + size - 1).execute().data or []
        if not rows:
            break
        for s in rows:
            base = derive_base_place(
                s.get('setting'), s.get('int_ext'),
                s.get('time_of_day'), s.get('location_hierarchy'),
            )
            canonical = alias_by_script.get(s['script_id'], {}).get(base, base)
            canonical = normalize_place(canonical)
            supabase.table('scenes').update(
                {'location_canonical': canonical}
            ).eq('id', s['id']).execute()
            updated += 1
        page += 1
        print(f"  ...{updated} scenes updated")

    print(f"Done. {updated} scenes backfilled.")


if __name__ == '__main__':
    main()
