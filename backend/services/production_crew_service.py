"""Crew assignments for a production (build-sequence step 2a).

A production_crew row joins a production to a contact with job-specific
detail. Owner-only — the route layer enforces via
production_service._user_owns_production.
"""
from services.production_service import get_supabase_admin
from services.department_service import valid_department_codes
from services.crew_import import parse_crew_csv
from services import department_service

ASSIGN_FIELDS = ("role", "department_code", "job_rate", "job_rate_unit",
                 "start_date", "end_date", "notes")


def _contacts_by_id(supabase, ids):
    if not ids:
        return {}
    rows = (supabase.table("contacts").select("*")
            .in_("id", list(ids)).execute().data or [])
    return {r["id"]: r for r in rows}


def _embed(supabase, crew_rows):
    contacts = _contacts_by_id(supabase, {c["contact_id"] for c in crew_rows})
    for c in crew_rows:
        c["contact"] = contacts.get(c["contact_id"])
    return crew_rows


def list_crew(production_id):
    supabase = get_supabase_admin()
    rows = (supabase.table("production_crew").select("*")
            .eq("production_id", production_id).execute().data or [])
    _embed(supabase, rows)
    rows.sort(key=lambda c: (
        c.get("department_code") is None,
        c.get("department_code") or "",
        (c.get("contact") or {}).get("name") or "",
    ))
    return rows


def _contact_owned_by(supabase, contact_id, user_id):
    res = (supabase.table("contacts").select("id")
           .eq("id", contact_id).eq("owner_id", user_id).limit(1).execute())
    return bool(res.data)


def add_crew(production_id, user_id, fields):
    supabase = get_supabase_admin()
    contact_id = fields.get("contact_id")
    if not contact_id or not _contact_owned_by(supabase, contact_id, user_id):
        return "bad_contact"
    dept = fields.get("department_code")
    if dept and dept not in valid_department_codes():
        return "bad_department"
    row = {"production_id": production_id, "contact_id": contact_id}
    for f in ASSIGN_FIELDS:
        if fields.get(f) is not None:
            row[f] = fields[f]
    created = supabase.table("production_crew").insert(row).execute().data[0]
    return _embed(supabase, [created])[0]


def _get_crew(supabase, production_id, crew_id):
    res = (supabase.table("production_crew").select("*")
           .eq("id", crew_id).eq("production_id", production_id).limit(1).execute())
    return res.data[0] if res.data else None


def update_crew(production_id, crew_id, fields):
    supabase = get_supabase_admin()
    if not _get_crew(supabase, production_id, crew_id):
        return "not_found"
    dept = fields.get("department_code")
    if dept and dept not in valid_department_codes():
        return "bad_department"
    patch = {f: fields[f] for f in ASSIGN_FIELDS if f in fields}
    if patch:
        supabase.table("production_crew").update(patch).eq("id", crew_id).execute()
    updated = _get_crew(supabase, production_id, crew_id)
    return _embed(supabase, [updated])[0]


def remove_crew(production_id, crew_id):
    (get_supabase_admin().table("production_crew").delete()
     .eq("id", crew_id).eq("production_id", production_id).execute())


def _find_contact_by_email(supabase, user_id, email):
    if not email:
        return None
    res = (supabase.table("contacts").select("*")
           .eq("owner_id", user_id).execute().data or [])
    for c in res:
        if (c.get("email") or "").strip().lower() == email.strip().lower():
            return c
    return None


def _has_same_role_assignment(supabase, production_id, contact_id, role):
    rows = (supabase.table("production_crew").select("role")
            .eq("production_id", production_id).eq("contact_id", contact_id)
            .execute().data or [])
    target = (role or "").strip().lower()
    return any((r.get("role") or "").strip().lower() == target for r in rows)


def import_crew_csv(production_id, user_id, csv_text):
    supabase = get_supabase_admin()
    depts = department_service.get_departments_list()
    valid_codes = {d["code"] for d in depts}
    name_to_code = {d["code"]: d["name"] for d in depts}

    parsed = parse_crew_csv(csv_text, valid_codes, name_to_code)
    if parsed["fatal"]:
        return ("fatal", parsed["fatal"])

    created = matched = assignments = 0
    skipped = list(parsed["errors"])

    for row in parsed["rows"]:
        contact = _find_contact_by_email(supabase, user_id, row["email"])
        if contact:
            matched += 1
        else:
            contact = supabase.table("contacts").insert({
                "owner_id": user_id, "created_by": user_id, "kind": "person",
                "name": row["name"], "email": row["email"], "phone": row["phone"],
                "company_name": row["company_name"], "role_tags": [],
                "standard_rate": row["rate"], "rate_unit": row["rate_unit"],
            }).execute().data[0]
            created += 1

        if _has_same_role_assignment(supabase, production_id, contact["id"], row["role"]):
            skipped.append({"line": 0, "reason": f"{row['name']} already on crew as {row['role'] or '(no role)'}"})
            continue

        supabase.table("production_crew").insert({
            "production_id": production_id, "contact_id": contact["id"],
            "role": row["role"], "department_code": row["department_code"],
            "job_rate": row["rate"], "job_rate_unit": row["rate_unit"],
            "notes": row["notes"],
        }).execute()
        assignments += 1

    return {"created_contacts": created, "matched_contacts": matched,
            "assignments_created": assignments, "skipped": skipped}
