"""Account-level contacts directory (build-sequence step 2a).

Owner-scoped, plus contacts on a production crew the caller manages
(see production_sharing). Contacts have no
script axis, so get_script_role is not involved.
"""
from db.supabase_client import get_supabase_admin
from services.production_sharing import shared_contact_ids, pooled_owner_ids

NOT_FOUND = object()

FIELDS = ("kind", "name", "company_name", "role_tags", "phone", "email",
          "agent_contact", "standard_rate", "rate_unit", "notes")

VALID_KINDS = frozenset(("person", "company"))
VALID_RATE_UNITS = frozenset(("day", "week", "flat"))


def _normalize_role_tags(value):
    if value is None:
        return []
    parts = value.split(",") if isinstance(value, str) else list(value)
    return [str(p).strip() for p in parts if str(p).strip()]


def _get(supabase, user_id, contact_id):
    """The contact if the caller owns it OR it is on a crew they manage."""
    res = (supabase.table("contacts").select("*")
           .eq("id", contact_id).eq("owner_id", user_id).limit(1).execute())
    if res.data:
        return res.data[0]
    if contact_id in shared_contact_ids(supabase, user_id):
        res = (supabase.table("contacts").select("*")
               .eq("id", contact_id).limit(1).execute())
        return res.data[0] if res.data else None
    return None


def _user_owns_contact(user_id, contact_id):
    return _get(get_supabase_admin(), user_id, contact_id) is not None


def list_contacts(user_id, q=None, kind=None, production_id=None):
    """Caller's own contacts; with `production_id`, the pooled contacts of that
    production's owner and admins (when the caller is one of them)."""
    supabase = get_supabase_admin()

    def _filtered(query):
        if kind:
            query = query.eq("kind", kind)
        if q:
            # Server-side substring search; strip PostgREST filter metacharacters
            # so a stray %/, can't break out of the or_ expression.
            needle = q.strip().replace("%", "").replace(",", "")
            if needle:
                query = query.or_(
                    f"name.ilike.%{needle}%,company_name.ilike.%{needle}%,email.ilike.%{needle}%")
        return query.order("name").execute().data or []

    rows = _filtered(supabase.table("contacts").select("*").eq("owner_id", user_id))
    if production_id:
        # Pool every production admin's address book, plus any attached crew contact.
        circle = pooled_owner_ids(supabase, user_id, production_id, "can_edit_crew")
        if circle:
            seen = {r["id"] for r in rows}
            extra = _filtered(supabase.table("contacts").select("*").in_("owner_id", list(circle)))
            extra += _filtered(supabase.table("contacts").select("*").in_(
                "id", list(shared_contact_ids(supabase, user_id, production_id)) or ["-"]))
            for r in extra:
                if r["id"] not in seen:
                    seen.add(r["id"])
                    rows.append(r)
            rows.sort(key=lambda r: (r.get("name") or "").lower())
    return rows


def create_contact(user_id, fields):
    supabase = get_supabase_admin()
    row = {"owner_id": user_id, "created_by": user_id,
           "name": fields["name"].strip(),
           "kind": fields.get("kind") or "person",
           "role_tags": _normalize_role_tags(fields.get("role_tags"))}
    for f in ("company_name", "phone", "email", "agent_contact",
              "standard_rate", "rate_unit", "notes"):
        if fields.get(f) is not None:
            row[f] = fields[f]
    return supabase.table("contacts").insert(row).execute().data[0]


def contact_usage(user_id, contact_id):
    supabase = get_supabase_admin()
    crew = (supabase.table("production_crew").select("production_id")
            .eq("contact_id", contact_id).execute().data or [])
    pids = {c["production_id"] for c in crew}
    if not pids:
        return []
    prods = (supabase.table("productions").select("id, title")
             .in_("id", list(pids)).execute().data or [])
    return [{"production_id": p["id"], "production_title": p.get("title")} for p in prods]


def get_contact_with_usage(user_id, contact_id):
    supabase = get_supabase_admin()
    contact = _get(supabase, user_id, contact_id)
    if not contact:
        return NOT_FOUND
    crew = (supabase.table("production_crew").select("*")
            .eq("contact_id", contact_id).execute().data or [])
    if not crew:
        return {"contact": contact, "assignments": []}
    prods = {p["id"]: p for p in (supabase.table("productions").select("id, title")
             .in_("id", list({c["production_id"] for c in crew})).execute().data or [])}
    assignments = [{
        "crew_id": c["id"], "production_id": c["production_id"],
        "production_title": prods.get(c["production_id"], {}).get("title"),
        "role": c.get("role"),
    } for c in crew]
    return {"contact": contact, "assignments": assignments}


def update_contact(user_id, contact_id, fields):
    supabase = get_supabase_admin()
    if not _get(supabase, user_id, contact_id):
        return NOT_FOUND
    patch = {}
    for f in FIELDS:
        if f in fields:
            patch[f] = _normalize_role_tags(fields[f]) if f == "role_tags" else fields[f]
    if "name" in patch:
        patch["name"] = (patch["name"] or "").strip()
    if not patch:
        return _get(supabase, user_id, contact_id)
    res = supabase.table("contacts").update(patch).eq("id", contact_id).execute()
    return res.data[0] if res.data else NOT_FOUND


def delete_contact(user_id, contact_id):
    supabase = get_supabase_admin()
    if not _get(supabase, user_id, contact_id):
        return "not_found"
    used = (supabase.table("production_crew").select("id")
            .eq("contact_id", contact_id).limit(1).execute().data or [])
    if used:
        return "in_use"
    supabase.table("contacts").delete().eq("id", contact_id).eq("owner_id", user_id).execute()
    return "ok"
