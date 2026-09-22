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
from services import call_sheet_template_service as tpl
from services import call_sheet_values as values
from services import call_sheet_render as render

NOT_FOUND = object()

DAY_INFO_FIELDS = (
    "weather", "sunrise_time", "sunset_time", "breakfast_time", "lunch_time",
    "nearest_hospital", "parking_notes", "safety_notes", "general_notes",
    "general_call",
)
_TIME_FIELDS = ("sunrise_time", "sunset_time", "breakfast_time", "lunch_time", "general_call")


def _safe_time(value):
    """HH:MM:SS -> HH:MM for display; leave anything unparseable untouched."""
    try:
        return values.normalize_time(value)
    except ValueError:
        return value


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


def _column_types(supabase, sheet, list_key):
    """{column_key: type} for cast_columns / crew_columns / scene_columns."""
    cfg = tpl.get_template(sheet["production_id"], supabase)["config"]
    return {c["key"]: c["type"] for c in cfg[list_key]}


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


def get_by_day(shooting_day_id):
    """Look up an existing call sheet for a shooting day WITHOUT creating one
    -- the read-only counterpart to get_or_create, gated at viewer level so a
    read-only production member can open a call sheet without ever needing
    the (edit-gated) POST get_or_create endpoint. Returns NOT_FOUND if no
    call sheet exists yet for this day."""
    supabase = get_supabase_admin()
    existing = (supabase.table("call_sheets").select("id")
                .eq("shooting_day_id", shooting_day_id).limit(1).execute())
    if not existing.data:
        return NOT_FOUND
    return get_call_sheet(existing.data[0]["id"])


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
    crew = _embed_crew(supabase, crew)
    cast = _embed_cast(supabase, cast)
    for r in crew + cast:
        r["call_time"] = _safe_time(r.get("call_time"))
    sheet = dict(row)
    for f in _TIME_FIELDS:
        if f in sheet:
            sheet[f] = _safe_time(sheet[f])
    template = tpl.get_template(row["production_id"], supabase)
    defaults = values.catering_defaults(crew, cast)
    return {
        **sheet,
        "crew": crew,
        "cast": cast,
        "locations": _embed_locations(supabase, locations),
        "scenes": get_day_scenes(supabase, row["shooting_day_id"]),
        "template": template["config"],
        "template_updated_at": template["updated_at"],
        "catering_defaults": defaults,
        "catering_effective": values.effective_catering(defaults, row.get("catering")),
    }


def _drop_sensitive_scalar_keys(incoming, sensitive_keys):
    """Split a flat {key: value} payload into (kept, dropped_keys) -- used to
    strip sensitive keys BEFORE they reach values.merge_values, so a writer
    without can_view_sensitive can't sneak a sensitive value in even though
    they'd never see it read back (redact_roster only filters responses)."""
    if not isinstance(incoming, dict) or not sensitive_keys:
        return incoming, []
    dropped = [k for k in incoming if k in sensitive_keys]
    if not dropped:
        return incoming, []
    return {k: v for k, v in incoming.items() if k not in sensitive_keys}, dropped


def _drop_sensitive_nested_keys(incoming, sensitive_inner_keys):
    """Same as _drop_sensitive_scalar_keys but for {outer: {inner: value}}
    payloads (scene_extras, dept_overrides, catering) -- strips sensitive
    inner keys per outer group. Returns (kept, dropped_paths) where dropped
    paths are reported as 'outer.inner', matching merge_nested's own
    ignored-key format."""
    if not isinstance(incoming, dict) or not sensitive_inner_keys:
        return incoming, []
    kept, dropped = {}, []
    for outer, inner in incoming.items():
        if isinstance(inner, dict):
            clean_inner, ign = _drop_sensitive_scalar_keys(inner, sensitive_inner_keys)
            dropped.extend(f"{outer}.{k}" for k in ign)
            kept[outer] = clean_inner
        else:
            kept[outer] = inner
    return kept, dropped


def update_call_sheet_with_report(call_sheet_id, fields, can_view_sensitive=True):
    """Returns (row | NOT_FOUND, ignored_keys). Raises ValueError on invalid values.
    JSONB payloads merge per key; unknown keys are ignored, not stored.

    `can_view_sensitive` gates writes too, not just the response redaction in
    redact_roster: a caller without it has any sensitive key in
    custom_values/dept_overrides/scene_extras/catering/header_values/
    block_overrides silently dropped before it ever reaches merge_values, and
    reported via the same ignored_keys list as unknown keys. Defaults to True
    so any caller that doesn't pass it explicitly keeps prior behaviour --
    the route layer is the one real caller and always passes the actual
    capability."""
    supabase = get_supabase_admin()
    sheet = _get(supabase, call_sheet_id)
    if not sheet:
        return NOT_FOUND, []
    cfg = tpl.get_template(sheet["production_id"], supabase)["config"]
    patch, ignored = {}, []

    for f in DAY_INFO_FIELDS:
        if f in fields:
            try:
                patch[f] = values.validate_value(tpl.BUILTIN_TYPES[f], fields[f])
            except ValueError as e:
                raise ValueError(f"{f}: {e}")
    if "status" in fields and fields["status"] in ("draft", "published"):
        patch["status"] = fields["status"]

    if "custom_values" in fields:
        types = {d["key"]: d["type"] for d in cfg["day_fields"] if not d["builtin"]}
        incoming = fields["custom_values"]
        if not can_view_sensitive:
            sensitive = {d["key"] for d in cfg["day_fields"] if not d["builtin"] and d.get("sensitive")}
            incoming, dropped = _drop_sensitive_scalar_keys(incoming, sensitive)
            ignored += dropped
        patch["custom_values"], ign = values.merge_values(
            sheet.get("custom_values"), incoming, types)
        ignored += ign
    if "dept_overrides" in fields:
        # departments carry no per-field sensitivity flag (see
        # call_sheet_template_service) -- nothing to drop here.
        patch["dept_overrides"], ign = values.merge_nested(
            sheet.get("dept_overrides"), fields["dept_overrides"],
            {d["key"] for d in cfg["departments"]}, {"call": "time", "as_per": "text"})
        ignored += ign
    if "scene_extras" in fields:
        scene_ids = {s["id"] for s in get_day_scenes(supabase, sheet["shooting_day_id"])}
        types = {c["key"]: c["type"] for c in cfg["scene_columns"]}
        incoming = fields["scene_extras"]
        if not can_view_sensitive:
            sensitive = _sensitive_keys(cfg, "scene_columns")
            incoming, dropped = _drop_sensitive_nested_keys(incoming, sensitive)
            ignored += dropped
        patch["scene_extras"], ign = values.merge_nested(
            sheet.get("scene_extras"), incoming, scene_ids, types)
        ignored += ign
    if "catering" in fields:
        # catering counts aren't template-column-flagged sensitive; nothing to drop.
        patch["catering"], ign = values.merge_nested(
            sheet.get("catering"), fields["catering"], set(values.MEALS),
            {g: "count" for g in values.CATERING_GROUPS})
        ignored += ign
    if "header_values" in fields:
        patch["header_values"], ign = values.merge_values(
            sheet.get("header_values"), fields["header_values"],
            {k["key"]: "text" for k in cfg["key_crew"]})
        ignored += ign
    if "block_overrides" in fields:
        patch["block_overrides"], ign = values.merge_values(
            sheet.get("block_overrides"), fields["block_overrides"],
            {b["key"]: "textarea" for b in cfg["blocks"]})
        ignored += ign

    if not patch:
        return _get(supabase, call_sheet_id), ignored
    res = (supabase.table("call_sheets").update(patch)
           .eq("id", call_sheet_id).execute())
    return (res.data[0] if res.data else NOT_FOUND), ignored


def update_call_sheet(call_sheet_id, fields, can_view_sensitive=True):
    return update_call_sheet_with_report(call_sheet_id, fields, can_view_sensitive)[0]


def _strip_sensitive_extra(supabase, sheet, list_key, extra, can_view_sensitive):
    """Drop sensitive `list_key` columns (crew_columns/cast_columns) from an
    `extra` payload before it reaches values.merge_values, when the caller
    lacks can_view_sensitive. Dropped keys are silently discarded -- same
    treatment as any other invalid/unknown key in this roster `extra`
    merge, per the module's existing pattern (no ignored_keys reporting here)."""
    if can_view_sensitive or not extra:
        return extra
    cfg = tpl.get_template(sheet["production_id"], supabase)["config"]
    sensitive = _sensitive_keys(cfg, list_key)
    if not sensitive:
        return extra
    return {k: v for k, v in extra.items() if k not in sensitive}


def add_crew(call_sheet_id, crew_id, call_time=None, notes=None, extra=None, can_view_sensitive=True):
    supabase = get_supabase_admin()
    sheet = _get(supabase, call_sheet_id)
    if not sheet:
        return "not_found"
    crew_res = (supabase.table("production_crew").select("*")
                .eq("id", crew_id).limit(1).execute())
    if not crew_res.data or crew_res.data[0].get("production_id") != sheet["production_id"]:
        return "cross_production"
    extra = _strip_sensitive_extra(supabase, sheet, "crew_columns", extra, can_view_sensitive)
    extra_clean, _ = values.merge_values(
        {}, extra or {}, _column_types(supabase, sheet, "crew_columns"))
    row = {"call_sheet_id": call_sheet_id, "crew_id": crew_id,
           "call_time": call_time, "notes": notes, "extra": extra_clean}
    created = supabase.table("call_sheet_crew").insert(row).execute().data[0]
    return _embed_crew(supabase, [created])[0]


def remove_crew(call_sheet_id, crew_id):
    (get_supabase_admin().table("call_sheet_crew").delete()
     .eq("call_sheet_id", call_sheet_id).eq("crew_id", crew_id).execute())


_CREW_CALL_FIELDS = ("call_time", "notes")


def update_crew_call(call_sheet_id, crew_id, fields, can_view_sensitive=True):
    """UPDATE (not insert) an existing call_sheet_crew row -- crew rows are
    added once via add_crew and then edited in place (a plain insert would
    collide with UNIQUE (call_sheet_id, crew_id)). `extra` merges per key."""
    supabase = get_supabase_admin()
    sheet = _get(supabase, call_sheet_id)
    if not sheet:
        return "not_found"
    existing = (supabase.table("call_sheet_crew").select("*")
                .eq("call_sheet_id", call_sheet_id).eq("crew_id", crew_id)
                .limit(1).execute())
    if not existing.data:
        return "not_found"
    patch = {f: fields[f] for f in _CREW_CALL_FIELDS if f in fields}
    if "extra" in fields:
        extra = _strip_sensitive_extra(supabase, sheet, "crew_columns", fields["extra"], can_view_sensitive)
        patch["extra"], _ = values.merge_values(
            existing.data[0].get("extra"), extra,
            _column_types(supabase, sheet, "crew_columns"))
    if not patch:
        return _embed_crew(supabase, existing.data)[0]
    res = (supabase.table("call_sheet_crew").update(patch)
           .eq("call_sheet_id", call_sheet_id).eq("crew_id", crew_id).execute())
    return _embed_crew(supabase, [res.data[0]])[0] if res.data else "not_found"


def add_cast(call_sheet_id, casting_id, call_time=None, status_code=None, notes=None, extra=None,
             can_view_sensitive=True):
    supabase = get_supabase_admin()
    sheet = _get(supabase, call_sheet_id)
    if not sheet:
        return "not_found"
    script_id = _script_id_for_day(supabase, sheet["shooting_day_id"])
    casting_res = (supabase.table("casting").select("*")
                   .eq("id", casting_id).limit(1).execute())
    if not casting_res.data or casting_res.data[0].get("script_id") != script_id:
        return "cross_script"
    extra = _strip_sensitive_extra(supabase, sheet, "cast_columns", extra, can_view_sensitive)
    extra_clean, _ = values.merge_values(
        {}, extra or {}, _column_types(supabase, sheet, "cast_columns"))
    row = {"call_sheet_id": call_sheet_id, "casting_id": casting_id,
           "call_time": call_time, "status_code": status_code, "notes": notes,
           "extra": extra_clean}
    created = supabase.table("call_sheet_cast").insert(row).execute().data[0]
    return _embed_cast(supabase, [created])[0]


def remove_cast(call_sheet_id, casting_id):
    (get_supabase_admin().table("call_sheet_cast").delete()
     .eq("call_sheet_id", call_sheet_id).eq("casting_id", casting_id).execute())


_CAST_CALL_FIELDS = ("call_time", "status_code", "notes")


def update_cast_call(call_sheet_id, casting_id, fields, can_view_sensitive=True):
    """UPDATE counterpart to add_cast -- same UNIQUE constraint rationale;
    `extra` merges per key."""
    supabase = get_supabase_admin()
    sheet = _get(supabase, call_sheet_id)
    if not sheet:
        return "not_found"
    existing = (supabase.table("call_sheet_cast").select("*")
                .eq("call_sheet_id", call_sheet_id).eq("casting_id", casting_id)
                .limit(1).execute())
    if not existing.data:
        return "not_found"
    patch = {f: fields[f] for f in _CAST_CALL_FIELDS if f in fields}
    if "extra" in fields:
        extra = _strip_sensitive_extra(supabase, sheet, "cast_columns", fields["extra"], can_view_sensitive)
        patch["extra"], _ = values.merge_values(
            existing.data[0].get("extra"), extra,
            _column_types(supabase, sheet, "cast_columns"))
    if not patch:
        return _embed_cast(supabase, existing.data)[0]
    res = (supabase.table("call_sheet_cast").update(patch)
           .eq("call_sheet_id", call_sheet_id).eq("casting_id", casting_id).execute())
    return _embed_cast(supabase, [res.data[0]])[0] if res.data else "not_found"


def add_location(call_sheet_id, location_id, is_primary=False):
    supabase = get_supabase_admin()
    sheet = _get(supabase, call_sheet_id)
    if not sheet:
        return "not_found"
    link_res = (supabase.table("production_locations").select("id")
                .eq("production_id", sheet["production_id"]).eq("location_id", location_id)
                .limit(1).execute())
    if not link_res.data:
        return "cross_production"
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


def _drop_keys(mapping, keys):
    """Return a copy of mapping with keys removed -- never mutates the
    original in place. redact_roster's inputs (crew/cast `extra`,
    scene_extras, custom_values) are references into rows fetched from the
    DB layer; mutating them in place would risk corrupting whatever object
    the caller (or, in the test double, the in-memory store) still holds."""
    if not isinstance(mapping, dict):
        return mapping
    return {k: v for k, v in mapping.items() if k not in keys}


def _sensitive_keys(template, list_key):
    return {c["key"] for c in template.get(list_key, []) if c.get("sensitive")}


def redact_roster(call_sheet_data, can_view_sensitive, template=None):
    """Strip rate fields (v1) plus any column/field the template flags
    `sensitive`. `template` falls back to the data's own, then the default.
    Builds redacted copies rather than mutating shared row/extra objects."""
    if can_view_sensitive:
        return call_sheet_data
    template = template or call_sheet_data.get("template") or tpl.default_config()

    if "crew" in call_sheet_data:
        crew_cols = _sensitive_keys(template, "crew_columns")
        new_rows = []
        for row in call_sheet_data["crew"]:
            row = dict(row)
            row["extra"] = _drop_keys(row.get("extra"), crew_cols)
            crew = row.get("crew")
            if isinstance(crew, dict):
                crew = dict(crew)
                for k in _SENSITIVE_CREW:
                    crew.pop(k, None)
                contact = crew.get("contact")
                if isinstance(contact, dict):
                    contact = dict(contact)
                    for k in _SENSITIVE_CONTACT:
                        contact.pop(k, None)
                    crew["contact"] = contact
                row["crew"] = crew
            new_rows.append(row)
        call_sheet_data["crew"] = new_rows

    if "cast" in call_sheet_data:
        cast_cols = _sensitive_keys(template, "cast_columns")
        call_sheet_data["cast"] = [
            {**row, "extra": _drop_keys(row.get("extra"), cast_cols)}
            for row in call_sheet_data["cast"]
        ]

    scene_extras = call_sheet_data.get("scene_extras")
    if isinstance(scene_extras, dict):
        scene_cols = _sensitive_keys(template, "scene_columns")
        call_sheet_data["scene_extras"] = {
            sid: _drop_keys(extras, scene_cols) for sid, extras in scene_extras.items()
        }

    custom_values = call_sheet_data.get("custom_values")
    custom_values = dict(custom_values) if isinstance(custom_values, dict) else custom_values
    for field in template.get("day_fields", []):
        if not field.get("sensitive"):
            continue
        if field.get("builtin"):
            if field["key"] in call_sheet_data:
                call_sheet_data[field["key"]] = None
        elif isinstance(custom_values, dict):
            custom_values.pop(field["key"], None)
    if isinstance(custom_values, dict):
        call_sheet_data["custom_values"] = custom_values

    return call_sheet_data


def _render_context(supabase, data, day):
    prod = (supabase.table("productions").select("title")
            .eq("id", data["production_id"]).limit(1).execute().data or [])
    days = (supabase.table("shooting_days").select("*")
            .eq("schedule_id", day.get("schedule_id")).execute().data or []) if day else []
    current = (day or {}).get("day_number") or 0
    later = [d for d in days if (d.get("day_number") or 0) > current]
    advanced = None
    if later:
        nxt = min(later, key=lambda d: d["day_number"])
        scenes = get_day_scenes(supabase, nxt["id"])
        if scenes:
            advanced = {"day": nxt, "scenes": scenes}
    return {
        "day": day,
        "production_title": prod[0].get("title") if prod else None,
        "days_total": len(days) or None,
        "advanced": advanced,
    }


def build_call_sheet_html(call_sheet_id, can_view_sensitive=False):
    supabase = get_supabase_admin()
    data = get_call_sheet(call_sheet_id)
    if data is NOT_FOUND:
        return NOT_FOUND
    data = redact_roster(data, can_view_sensitive)
    day_res = (supabase.table("shooting_days").select("*")
               .eq("id", data["shooting_day_id"]).limit(1).execute())
    day = day_res.data[0] if day_res.data else {}
    return render.render_html(data, _render_context(supabase, data, day))


def render_call_sheet_pdf(call_sheet_id, can_view_sensitive=False):
    if not WEASYPRINT_AVAILABLE:
        raise ImportError("weasyprint is not installed")
    html_content = build_call_sheet_html(call_sheet_id, can_view_sensitive)
    if html_content is NOT_FOUND:
        return NOT_FOUND
    css = report_service._get_report_css()
    from weasyprint import CSS
    return HTML(string=html_content).write_pdf(stylesheets=[CSS(string=css)])
