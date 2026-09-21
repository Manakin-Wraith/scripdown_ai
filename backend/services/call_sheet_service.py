"""Call sheet CRUD, roster/location assembly, and PDF rendering
(build-sequence step 4).

Gated at the route layer by middleware.production_authz.require_production_role
-- this module trusts its caller already passed that check. See
docs/superpowers/specs/2026-09-18-call-sheets-design.md for the full design,
including the "permission-system fork" note on why this is production-authz
scoped despite being anchored to a shooting_day (script-role world).
"""
from db.supabase_client import get_supabase_admin

try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

from services.report_service import report_service
from services import department_service

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


def update_call_sheet(call_sheet_id, fields):
    supabase = get_supabase_admin()
    if not _get(supabase, call_sheet_id):
        return NOT_FOUND
    patch = {f: fields[f] for f in DAY_INFO_FIELDS if f in fields}
    if "status" in fields and fields["status"] in ("draft", "published"):
        patch["status"] = fields["status"]
    if not patch:
        return _get(supabase, call_sheet_id)
    res = (supabase.table("call_sheets").update(patch)
           .eq("id", call_sheet_id).execute())
    return res.data[0] if res.data else NOT_FOUND


def add_crew(call_sheet_id, crew_id, call_time=None, notes=None):
    supabase = get_supabase_admin()
    sheet = _get(supabase, call_sheet_id)
    if not sheet:
        return "not_found"
    crew_res = (supabase.table("production_crew").select("*")
                .eq("id", crew_id).limit(1).execute())
    if not crew_res.data or crew_res.data[0].get("production_id") != sheet["production_id"]:
        return "cross_production"
    row = {"call_sheet_id": call_sheet_id, "crew_id": crew_id,
           "call_time": call_time, "notes": notes}
    created = supabase.table("call_sheet_crew").insert(row).execute().data[0]
    return _embed_crew(supabase, [created])[0]


def remove_crew(call_sheet_id, crew_id):
    (get_supabase_admin().table("call_sheet_crew").delete()
     .eq("call_sheet_id", call_sheet_id).eq("crew_id", crew_id).execute())


def add_cast(call_sheet_id, casting_id, call_time=None, status_code=None, notes=None):
    supabase = get_supabase_admin()
    sheet = _get(supabase, call_sheet_id)
    if not sheet:
        return "not_found"
    script_id = _script_id_for_day(supabase, sheet["shooting_day_id"])
    casting_res = (supabase.table("casting").select("*")
                   .eq("id", casting_id).limit(1).execute())
    if not casting_res.data or casting_res.data[0].get("script_id") != script_id:
        return "cross_script"
    row = {"call_sheet_id": call_sheet_id, "casting_id": casting_id,
           "call_time": call_time, "status_code": status_code, "notes": notes}
    created = supabase.table("call_sheet_cast").insert(row).execute().data[0]
    return _embed_cast(supabase, [created])[0]


def remove_cast(call_sheet_id, casting_id):
    (get_supabase_admin().table("call_sheet_cast").delete()
     .eq("call_sheet_id", call_sheet_id).eq("casting_id", casting_id).execute())


def add_location(call_sheet_id, location_id, is_primary=False):
    supabase = get_supabase_admin()
    if not _get(supabase, call_sheet_id):
        return "not_found"
    if is_primary:
        (supabase.table("call_sheet_locations").update({"is_primary": False})
         .eq("call_sheet_id", call_sheet_id).execute())
    row = {"call_sheet_id": call_sheet_id, "location_id": location_id, "is_primary": bool(is_primary)}
    created = supabase.table("call_sheet_locations").insert(row).execute().data[0]
    return _embed_locations(supabase, [created])[0]


def remove_location(call_sheet_id, location_id):
    (get_supabase_admin().table("call_sheet_locations").delete()
     .eq("call_sheet_id", call_sheet_id).eq("location_id", location_id).execute())


# Call-sheet-specific redaction. NOT production_crew_service._redact(): that
# function bundles job_rate (crew) with phone AND standard_rate (contact) as
# one all-or-nothing unit, so it can't isolate "hide rate, keep phone." A
# call sheet's entire purpose is day-of contact info, so phone/email are
# always shown to anyone who can view the sheet -- only rate fields are
# gated by can_view_sensitive.
_SENSITIVE_CREW = ("job_rate",)
_SENSITIVE_CONTACT = ("standard_rate",)


def redact_roster(call_sheet_data, can_view_sensitive):
    if can_view_sensitive:
        return call_sheet_data
    for row in call_sheet_data.get("crew", []):
        crew = row.get("crew")
        if isinstance(crew, dict):
            for k in _SENSITIVE_CREW:
                crew.pop(k, None)
            contact = crew.get("contact")
            if isinstance(contact, dict):
                for k in _SENSITIVE_CONTACT:
                    contact.pop(k, None)
    return call_sheet_data


def _esc(value):
    import html as _html
    return _html.escape(str(value)) if value is not None else ""


def _render_pdf_html(data, day):
    status = data.get("status", "draft")
    draft_banner = '<div class="cs-draft-banner">DRAFT</div>' if status == "draft" else ""

    day_info = (
        f'<div class="cs-day-info">'
        f'<span>Weather: {_esc(data.get("weather") or "-")}</span>'
        f'<span>Sunrise: {_esc(data.get("sunrise_time") or "-")}</span>'
        f'<span>Sunset: {_esc(data.get("sunset_time") or "-")}</span>'
        f'<span>Breakfast: {_esc(data.get("breakfast_time") or "-")}</span>'
        f'<span>Lunch: {_esc(data.get("lunch_time") or "-")}</span>'
        f'</div>'
    )

    locs = sorted(data.get("locations", []), key=lambda r: (not r.get("is_primary"), r.get("sort_order", 0)))
    loc_html = "".join(
        f'<div class="cs-location"><strong>{_esc((l.get("location") or {}).get("name"))}</strong>'
        f'{" (Primary)" if l.get("is_primary") else ""}<br>'
        f'{_esc((l.get("location") or {}).get("address") or "")}<br>'
        f'Parking: {_esc((l.get("location") or {}).get("parking_notes") or "-")}</div>'
        for l in locs
    )

    scene_rows = "".join(
        f'<tr><td>{_esc(s.get("scene_number"))}</td><td>{_esc(s.get("int_ext"))}</td>'
        f'<td>{_esc(s.get("setting") or s.get("location_canonical"))}</td>'
        f'<td>{_esc(s.get("time_of_day"))}</td><td>{s.get("page_length_eighths", 8)}/8</td></tr>'
        for s in data.get("scenes", [])
    )

    cast_rows = "".join(
        f'<tr><td>{_esc((c.get("casting") or {}).get("character_name"))}</td>'
        f'<td>{_esc((c.get("casting") or {}).get("actor_name"))}</td>'
        f'<td>{_esc(c.get("status_code") or "")}</td><td>{_esc(c.get("call_time") or "")}</td></tr>'
        for c in data.get("cast", [])
    )

    dept_order = [d["code"] for d in department_service.get_departments_list()]
    crew_rows = data.get("crew", [])
    crew_by_dept = {}
    for row in crew_rows:
        code = (row.get("crew") or {}).get("department_code")
        crew_by_dept.setdefault(code, []).append(row)
    crew_sections = []
    for code in dept_order + [c for c in crew_by_dept if c not in dept_order]:
        rows = crew_by_dept.get(code)
        if not rows:
            continue
        label = department_service.get_department_name(code) if code else "Other"
        rows_html = "".join(
            f'<tr><td>{_esc((r.get("crew") or {}).get("contact", {}).get("name"))}</td>'
            f'<td>{_esc((r.get("crew") or {}).get("role") or "")}</td>'
            f'<td>{_esc(r.get("call_time") or "")}</td></tr>'
            for r in rows
        )
        crew_sections.append(f'<h4>{_esc(label)}</h4><table class="report-table">{rows_html}</table>')

    return f"""
    <html><body>
    {draft_banner}
    <div class="cs-header"><h1>Day {day.get("day_number")} &middot; {_esc(day.get("shoot_date") or "")}</h1></div>
    {day_info}
    <h3>Locations</h3>{loc_html}
    <h3>Scene Schedule</h3><table class="report-table">
      <thead><tr><th>Sc</th><th>I/E</th><th>Set</th><th>D/N</th><th>Pgs</th></tr></thead>
      <tbody>{scene_rows}</tbody></table>
    <h3>Cast Call List</h3><table class="report-table">
      <thead><tr><th>Character</th><th>Actor</th><th>Status</th><th>Call Time</th></tr></thead>
      <tbody>{cast_rows}</tbody></table>
    <h3>Crew Call List</h3>{''.join(crew_sections)}
    <div class="cs-footer">
      <p>Nearest Hospital: {_esc(data.get("nearest_hospital") or "-")}</p>
      <p>Safety/COVID: {_esc(data.get("safety_notes") or "-")}</p>
      <p>{_esc(data.get("general_notes") or "")}</p>
    </div>
    </body></html>
    """


def render_call_sheet_pdf(call_sheet_id):
    if not WEASYPRINT_AVAILABLE:
        raise ImportError("weasyprint is not installed")
    supabase = get_supabase_admin()
    data = get_call_sheet(call_sheet_id)
    if data is NOT_FOUND:
        return NOT_FOUND
    day_res = (supabase.table("shooting_days").select("*")
               .eq("id", data["shooting_day_id"]).limit(1).execute())
    day = day_res.data[0] if day_res.data else {}
    html_content = _render_pdf_html(data, day)
    css = report_service._get_report_css()
    from weasyprint import CSS
    return HTML(string=html_content).write_pdf(stylesheets=[CSS(string=css)])
