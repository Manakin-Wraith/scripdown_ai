"""Call sheet CRUD, roster/location assembly, and PDF rendering
(build-sequence step 4).

Gated at the route layer by middleware.production_authz.require_production_role
-- this module trusts its caller already passed that check. See
docs/superpowers/specs/2026-09-18-call-sheets-design.md for the full design,
including the "permission-system fork" note on why this is production-authz
scoped despite being anchored to a shooting_day (script-role world).
"""
from db.supabase_client import get_supabase_admin

NOT_FOUND = object()

DAY_INFO_FIELDS = (
    "weather", "sunrise_time", "sunset_time", "breakfast_time", "lunch_time",
    "nearest_hospital", "parking_notes", "safety_notes", "general_notes",
)


def _resolve_production_id(supabase, shooting_day_id):
    """shooting_day -> shooting_schedule -> script -> scripts.production_id.
    None if the day doesn't exist OR the script has no production."""
    day_res = (supabase.table("shooting_days").select("schedule_id")
               .eq("id", shooting_day_id).limit(1).execute())
    if not day_res.data:
        return None
    sched_res = (supabase.table("shooting_schedules").select("script_id")
                 .eq("id", day_res.data[0].get("schedule_id")).limit(1).execute())
    if not sched_res.data:
        return None
    script_id = sched_res.data[0].get("script_id")
    script_res = (supabase.table("scripts").select("production_id")
                  .eq("id", script_id).limit(1).execute())
    if not script_res.data:
        return None
    return script_res.data[0].get("production_id"), script_id


def _script_id_for_day(supabase, shooting_day_id):
    """Just the script_id (used by add_cast's cross-script check)."""
    day_res = (supabase.table("shooting_days").select("schedule_id")
               .eq("id", shooting_day_id).limit(1).execute())
    if not day_res.data:
        return None
    sched_res = (supabase.table("shooting_schedules").select("script_id")
                 .eq("id", day_res.data[0].get("schedule_id")).limit(1).execute())
    return sched_res.data[0].get("script_id") if sched_res.data else None


def _get(supabase, call_sheet_id):
    res = (supabase.table("call_sheets").select("*")
           .eq("id", call_sheet_id).limit(1).execute())
    return res.data[0] if res.data else None


def get_or_create(shooting_day_id, user_id):
    """Idempotent: returns the existing call_sheets row for this day, or
    creates one. Returns the string 'no_production' if the day doesn't
    exist or its script has no production association -- callers map this
    to a 404 (indistinguishable from "day doesn't exist" per the spec's
    corrected error-shape note; the route's require_production_role
    decorator gives the same 404 for both cases before this function is
    even reached in the normal flow, but get_or_create is also exercised
    directly in these service tests)."""
    supabase = get_supabase_admin()
    existing = (supabase.table("call_sheets").select("*")
                .eq("shooting_day_id", shooting_day_id).limit(1).execute())
    if existing.data:
        return existing.data[0]
    resolved = _resolve_production_id(supabase, shooting_day_id)
    if not resolved or not resolved[0]:
        return "no_production"
    production_id, _script_id = resolved
    row = {"production_id": production_id, "shooting_day_id": shooting_day_id,
           "status": "draft", "created_by": user_id}
    return supabase.table("call_sheets").insert(row).execute().data[0]


def _embed_crew(supabase, rows):
    if not rows:
        return rows
    crew_ids = {r["crew_id"] for r in rows}
    crew = (supabase.table("production_crew").select("*")
            .in_("id", list(crew_ids)).execute().data or [])
    crew_by_id = {c["id"]: c for c in crew}
    contact_ids = {c["contact_id"] for c in crew if c.get("contact_id")}
    contacts = (supabase.table("contacts").select("*")
                .in_("id", list(contact_ids)).execute().data or []) if contact_ids else []
    contacts_by_id = {c["id"]: c for c in contacts}
    for r in rows:
        crew_row = dict(crew_by_id.get(r["crew_id"]) or {})
        crew_row["contact"] = contacts_by_id.get(crew_row.get("contact_id"))
        r["crew"] = crew_row
    return rows


def _embed_cast(supabase, rows):
    if not rows:
        return rows
    casting_ids = {r["casting_id"] for r in rows}
    casting = (supabase.table("casting").select("*")
               .in_("id", list(casting_ids)).execute().data or [])
    casting_by_id = {c["id"]: c for c in casting}
    for r in rows:
        r["casting"] = casting_by_id.get(r["casting_id"])
    return rows


def _embed_locations(supabase, rows):
    if not rows:
        return rows
    location_ids = {r["location_id"] for r in rows}
    locations = (supabase.table("locations").select("*")
                 .in_("id", list(location_ids)).execute().data or [])
    locations_by_id = {l["id"]: l for l in locations}
    for r in rows:
        r["location"] = locations_by_id.get(r["location_id"])
    return rows


def get_day_scenes(supabase, shooting_day_id):
    """The day's live scene list -- NOT stored on the call sheet, read fresh
    from shooting_day_scenes + scenes every time. A scene reassigned to a
    different day stays in sync automatically while the sheet is draft."""
    ds_rows = (supabase.table("shooting_day_scenes").select("*")
               .eq("shooting_day_id", shooting_day_id)
               .order("sort_order", desc=False).execute().data or [])
    scene_ids = {r["scene_id"] for r in ds_rows}
    scenes = (supabase.table("scenes").select("*")
              .in_("id", list(scene_ids)).execute().data or []) if scene_ids else []
    scenes_by_id = {s["id"]: s for s in scenes}
    ordered = []
    for ds in ds_rows:
        s = scenes_by_id.get(ds["scene_id"])
        if s:
            ordered.append(s)
    return ordered


def get_call_sheet(call_sheet_id):
    supabase = get_supabase_admin()
    row = _get(supabase, call_sheet_id)
    if not row:
        return NOT_FOUND
    crew = (supabase.table("call_sheet_crew").select("*")
            .eq("call_sheet_id", call_sheet_id).execute().data or [])
    cast = (supabase.table("call_sheet_cast").select("*")
            .eq("call_sheet_id", call_sheet_id).execute().data or [])
    locations = (supabase.table("call_sheet_locations").select("*")
                 .eq("call_sheet_id", call_sheet_id)
                 .order("sort_order", desc=False).execute().data or [])
    return {
        **row,
        "crew": _embed_crew(supabase, crew),
        "cast": _embed_cast(supabase, cast),
        "locations": _embed_locations(supabase, locations),
        "scenes": get_day_scenes(supabase, row["shooting_day_id"]),
    }
