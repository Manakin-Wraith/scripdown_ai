"""Config-driven call sheet HTML renderer.

Pure: takes the assembled (already redacted) call sheet dict plus a render
context and returns HTML for WeasyPrint. No DB access. All user-authored text
is escaped. See docs/superpowers/specs/2026-09-21-call-sheet-customization-design.md.
"""
import html as _html

from services import department_service
from services import call_sheet_values as values
from services.call_sheet_template_service import default_config

# Repeats a compact header on every page (WeasyPrint running element).
CSS_EXTRA = """
@page { margin-top: 22mm; @top-center { content: element(csrunning); font-size: 9pt; color: #555; } }
.cs-running { position: running(csrunning); }
.cs-section { margin-bottom: 10px; }
.cs-field { margin: 2px 0; }
.cs-block { margin: 6px 0; }
.cs-key-crew span { margin-right: 14px; }
"""


def esc(value):
    return _html.escape(str(value)) if value is not None else ""


def _fmt(ftype, value):
    text = esc(value)
    if ftype == "link" and str(value).lower().startswith(("http://", "https://")):
        return f'<a href="{text}">{text}</a>'
    if ftype == "textarea":
        return f'<span style="white-space: pre-wrap">{text}</span>'
    return text


def _cell(column, value):
    return "" if value in (None, "") else _fmt(column["type"], value)


def _effective(field, data):
    if field.get("builtin"):
        value = data.get(field["key"])
    else:
        value = (data.get("custom_values") or {}).get(field["key"])
    if value in (None, ""):
        value = field.get("default") or ""
    return value


def _fields_html(data, cfg, section):
    out = []
    for field in cfg.get("day_fields", []):
        if field.get("section") != section or not field.get("visible", True):
            continue
        value = _effective(field, data)
        if value in (None, ""):
            continue
        out.append(f'<div class="cs-field"><strong>{esc(field["label"])}:</strong> '
                   f'{_fmt(field["type"], value)}</div>')
    return "".join(out)


def _key_crew_html(data, cfg):
    overrides = data.get("header_values") or {}
    spans = []
    for entry in cfg.get("key_crew", []):
        value = overrides.get(entry["key"], entry.get("value", ""))
        if value:
            spans.append(f'<span><strong>{esc(entry["label"])}:</strong> {esc(value)}</span>')
    return f'<div class="cs-key-crew">{"".join(spans)}</div>' if spans else ""


def split_cast(data, cfg):
    """(main_rows, extras_rows). Background-tier rows only leave the cast table
    when the extras section is visible, so hiding it never drops anyone."""
    rows = data.get("cast", [])
    extras_visible = any(s["key"] == "extras" and s.get("visible", True) for s in cfg["sections"])
    if not extras_visible:
        return rows, []
    bg = [r for r in rows if (r.get("casting") or {}).get("tier") == "background"]
    return [r for r in rows if r not in bg], bg


def _cast_table(rows, cfg, first_labels=("Character", "Actor", "Status", "Call Time")):
    cols = cfg.get("cast_columns", [])
    head = "".join(f"<th>{esc(h)}</th>" for h in first_labels) + \
        "".join(f'<th>{esc(c["label"])}</th>' for c in cols)
    body = ""
    for row in rows:
        casting = row.get("casting") or {}
        extra = row.get("extra") or {}
        body += (f'<tr><td>{esc(casting.get("character_name"))}</td>'
                 f'<td>{esc(casting.get("actor_name"))}</td>'
                 f'<td>{esc(row.get("status_code") or "")}</td>'
                 f'<td>{esc(row.get("call_time") or "")}</td>'
                 + "".join(f'<td>{_cell(c, extra.get(c["key"]))}</td>' for c in cols)
                 + "</tr>")
    return f'<table class="report-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


# ---------- section renderers: (data, cfg, ctx) -> html | None ----------

def _render_header(data, cfg, ctx):
    day = ctx.get("day") or {}
    day_line = f'Day {esc(day.get("day_number"))}'
    if ctx.get("days_total"):
        day_line += f' of {esc(ctx["days_total"])}'
    if day.get("shoot_date"):
        day_line += f' &middot; {esc(day["shoot_date"])}'
    title = f'<h1>{esc(ctx["production_title"])}</h1>' if ctx.get("production_title") else ""
    return (f'<div class="cs-header">{title}<h2>{day_line}</h2>'
            f'{_fields_html(data, cfg, "header")}{_key_crew_html(data, cfg)}</div>')


def _render_day_info(data, cfg, ctx):
    return f'<div class="cs-day-info">{_fields_html(data, cfg, "day_info")}</div>'


def _render_locations(data, cfg, ctx):
    locs = sorted(data.get("locations", []),
                  key=lambda r: (not r.get("is_primary"), r.get("sort_order", 0)))
    return "".join(
        f'<div class="cs-location"><strong>{esc((l.get("location") or {}).get("name"))}</strong>'
        f'{" (Primary)" if l.get("is_primary") else ""}<br>'
        f'{esc((l.get("location") or {}).get("address") or "")}<br>'
        f'Parking: {esc((l.get("location") or {}).get("parking_notes") or "-")}</div>'
        for l in locs)


def _render_scenes(data, cfg, ctx):
    cols = cfg.get("scene_columns", [])
    extras = data.get("scene_extras") or {}
    head = "<th>Sc</th><th>I/E</th><th>Set</th><th>D/N</th><th>Pgs</th>" + \
        "".join(f'<th>{esc(c["label"])}</th>' for c in cols)
    body = ""
    for s in data.get("scenes", []):
        ex = extras.get(s.get("id")) or {}
        body += (f'<tr><td>{esc(s.get("scene_number"))}</td><td>{esc(s.get("int_ext"))}</td>'
                 f'<td>{esc(s.get("setting") or s.get("location_canonical"))}</td>'
                 f'<td>{esc(s.get("time_of_day"))}</td>'
                 f'<td>{esc(s.get("page_length_eighths", 8))}/8</td>'
                 + "".join(f'<td>{_cell(c, ex.get(c["key"]))}</td>' for c in cols) + "</tr>")
    return f'<table class="report-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def _render_cast(data, cfg, ctx):
    main, _ = split_cast(data, cfg)
    return _cast_table(main, cfg)


def _render_crew(data, cfg, ctx):
    cols = cfg.get("crew_columns", [])
    dept_order = [d["code"] for d in department_service.get_departments_list()]
    by_dept = {}
    for row in data.get("crew", []):
        by_dept.setdefault((row.get("crew") or {}).get("department_code"), []).append(row)
    head = "<th>Name</th><th>Role</th><th>Call</th>" + \
        "".join(f'<th>{esc(c["label"])}</th>' for c in cols)
    sections = []
    for code in dept_order + [c for c in by_dept if c not in dept_order]:
        rows = by_dept.get(code)
        if not rows:
            continue
        label = department_service.get_department_name(code) if code else "Other"
        body = "".join(
            f'<tr><td>{esc(((r.get("crew") or {}).get("contact") or {}).get("name"))}</td>'
            f'<td>{esc((r.get("crew") or {}).get("role") or "")}</td>'
            f'<td>{esc(r.get("call_time") or "")}</td>'
            + "".join(f'<td>{_cell(c, (r.get("extra") or {}).get(c["key"]))}</td>' for c in cols)
            + "</tr>" for r in rows)
        sections.append(f'<h4>{esc(label)}</h4><table class="report-table">'
                        f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>')
    return "".join(sections)


def _render_notes(data, cfg, ctx):
    overrides = data.get("block_overrides") or {}
    blocks = ""
    for block in cfg.get("blocks", []):
        body = overrides.get(block["key"], block.get("body", ""))
        if body and body.strip():
            blocks += (f'<div class="cs-block"><strong>{esc(block["label"])}</strong>'
                       f'<div style="white-space: pre-wrap">{esc(body)}</div></div>')
    return _fields_html(data, cfg, "notes") + blocks


GROUP_LABELS = (("crew", "Crew"), ("cast", "Cast"), ("add_crew", "Add. crew"), ("extras", "Extras"))
MEAL_LABELS = (("craft", "Craft"), ("breakfast", "Breakfast"), ("lunch", "Lunch"), ("dinner", "Dinner"))


def _render_extras(data, cfg, ctx):
    _, extras = split_cast(data, cfg)
    if not extras:
        return None
    return _cast_table(extras, cfg, first_labels=("Role", "Name", "Status", "Call Time"))


def _render_dept_calls(data, cfg, ctx):
    overrides = data.get("dept_overrides") or {}
    rows = ""
    for dept in cfg.get("departments", []):
        ov = overrides.get(dept["key"]) or {}
        call = ov.get("call") or dept.get("default_call") or ""
        as_per = ov.get("as_per") or dept.get("as_per") or ""
        if call or as_per:
            rows += f'<tr><td>{esc(dept["label"])}</td><td>{esc(call)}</td><td>{esc(as_per)}</td></tr>'
    if not rows:
        return None
    return ('<table class="report-table"><thead><tr><th>Department</th><th>Call</th>'
            f'<th>As per</th></tr></thead><tbody>{rows}</tbody></table>')


def _render_catering(data, cfg, ctx):
    eff = data.get("catering_effective") or values.effective_catering(
        values.catering_defaults(data.get("crew", []), data.get("cast", [])), data.get("catering"))
    totals = {m: sum(eff.get(m, {}).get(g, 0) for g, _ in GROUP_LABELS) for m, _ in MEAL_LABELS}
    if not any(totals.values()):
        return None
    head = "<th></th>" + "".join(f"<th>{label}</th>" for _, label in MEAL_LABELS)
    rows = "".join(
        f"<tr><td>{glabel}</td>"
        + "".join(f'<td>{esc(eff.get(m, {}).get(g, 0))}</td>' for m, _ in MEAL_LABELS) + "</tr>"
        for g, glabel in GROUP_LABELS)
    total_row = "<tr><td><strong>Total</strong></td>" + \
        "".join(f"<td>{esc(totals[m])}</td>" for m, _ in MEAL_LABELS) + "</tr>"
    return f'<table class="report-table"><thead><tr>{head}</tr></thead><tbody>{rows}{total_row}</tbody></table>'


def _render_advanced(data, cfg, ctx):
    adv = ctx.get("advanced")
    if not adv:
        return None
    day = adv["day"]
    caption = f'<p>Day {esc(day.get("day_number"))} &middot; {esc(day.get("shoot_date") or "")}</p>'
    rows = "".join(
        f'<tr><td>{esc(s.get("scene_number"))}</td><td>{esc(s.get("int_ext"))}</td>'
        f'<td>{esc(s.get("setting") or s.get("location_canonical"))}</td>'
        f'<td>{esc(s.get("time_of_day"))}</td><td>{esc(s.get("page_length_eighths", 8))}/8</td></tr>'
        for s in adv["scenes"])
    return (f'{caption}<table class="report-table"><thead><tr><th>Sc</th><th>I/E</th><th>Set</th>'
            f'<th>D/N</th><th>Pgs</th></tr></thead><tbody>{rows}</tbody></table>')


SECTION_RENDERERS = {
    "header": _render_header,
    "day_info": _render_day_info,
    "locations": _render_locations,
    "scenes": _render_scenes,
    "cast": _render_cast,
    "extras": _render_extras,
    "crew": _render_crew,
    "dept_calls": _render_dept_calls,
    "catering": _render_catering,
    "notes": _render_notes,
    "advanced": _render_advanced,
}


def render_html(data, ctx):
    cfg = data.get("template") or default_config()
    day = ctx.get("day") or {}
    banner = '<div class="cs-draft-banner">DRAFT</div>' if data.get("status", "draft") == "draft" else ""
    running = (f'<div class="cs-running">{esc(ctx.get("production_title") or "")} &middot; '
               f'Day {esc(day.get("day_number"))} &middot; {esc(day.get("shoot_date") or "")}</div>')
    body = []
    for section in cfg["sections"]:
        if not section.get("visible", True):
            continue
        renderer = SECTION_RENDERERS.get(section["key"])
        if renderer is None:
            continue
        inner = renderer(data, cfg, ctx)
        if inner is None:
            continue
        heading = "" if section["key"] == "header" else f'<h3>{esc(section["label"])}</h3>'
        body.append(f'<section class="cs-section cs-section-{section["key"]}">{heading}{inner}</section>')
    return (f"<html><head><style>{CSS_EXTRA}</style></head><body>"
            f"{running}{banner}{''.join(body)}</body></html>")
