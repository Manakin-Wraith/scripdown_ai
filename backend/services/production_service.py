"""
Production data logic (build-sequence step 1 -- "the spine").

A production is a physical-shoot container holding >=0 scripts. Access:
owner-only for list/write; GET-one also serves a team member who holds a
role on a script inside the production (mirrors series_routes.py). No
production_members table yet -- that ships with the crew slice.
"""
from db.supabase_client import get_supabase_admin
from middleware.authorization import get_script_role, SCRIPT_NOT_FOUND

NOT_FOUND = object()  # distinguishes 404 from 403 to the route layer

_EDITABLE_FIELDS = ("title", "status", "shoot_start_date", "shoot_end_date", "notes")


def _get_production(supabase, production_id):
    res = (supabase.table("productions").select("*")
           .eq("id", production_id).limit(1).execute())
    return res.data[0] if res.data else None


def _user_owns_production(production_id, user_id):
    prod = _get_production(get_supabase_admin(), production_id)
    return bool(prod and prod.get("owner_id") == user_id)


def create_production(user_id, fields):
    supabase = get_supabase_admin()
    row = {"owner_id": user_id, "created_by": user_id,
           "title": fields["title"],
           "status": fields.get("status") or "development"}
    for f in ("shoot_start_date", "shoot_end_date", "notes"):
        if fields.get(f) is not None:
            row[f] = fields[f]
    prod = supabase.table("productions").insert(row).execute().data[0]
    unit = supabase.table("units").insert({
        "production_id": prod["id"], "name": "Main Unit", "sort_order": 0,
    }).execute().data[0]
    return {"production": prod, "unit": unit}


def list_productions(user_id):
    supabase = get_supabase_admin()
    res = (supabase.table("productions").select("*")
           .eq("owner_id", user_id).order("created_at", desc=True).execute())
    return res.data or []


def _accessible_scripts(supabase, production_id, user_id, is_owner):
    res = (supabase.table("scripts").select("*")
           .eq("production_id", production_id).execute())
    scripts = res.data or []
    if is_owner:
        return scripts
    visible = []
    for s in scripts:
        role = get_script_role(s["id"], user_id)
        if role not in (None, SCRIPT_NOT_FOUND):
            visible.append(s)
    return visible


def get_production_for_viewer(production_id, user_id):
    supabase = get_supabase_admin()
    prod = _get_production(supabase, production_id)
    if not prod:
        return NOT_FOUND
    is_owner = prod.get("owner_id") == user_id
    scripts = _accessible_scripts(supabase, production_id, user_id, is_owner)
    if not is_owner and not scripts:
        return None  # exists, but caller has no way in
    return {"production": prod, "scripts": scripts}


def update_production(production_id, fields):
    supabase = get_supabase_admin()
    patch = {f: fields[f] for f in _EDITABLE_FIELDS if f in fields}
    if not patch:
        return _get_production(supabase, production_id)
    res = (supabase.table("productions").update(patch)
           .eq("id", production_id).execute())
    return res.data[0] if res.data else None


def delete_production(production_id):
    get_supabase_admin().table("productions").delete().eq("id", production_id).execute()


def add_script(production_id, script_id, user_id):
    """Single conditional UPDATE -- no read-then-write race.

    Returns 'ok' | 'not_owned' | 'conflict'.
    """
    supabase = get_supabase_admin()
    owned = (supabase.table("scripts").select("id")
             .eq("id", script_id).eq("user_id", user_id).limit(1).execute())
    if not owned.data:
        return "not_owned"
    res = (supabase.table("scripts")
           .update({"production_id": production_id})
           .eq("id", script_id).eq("user_id", user_id)
           .is_("production_id", "null")
           .execute())
    return "ok" if res.data else "conflict"


def remove_script(production_id, script_id):
    (get_supabase_admin().table("scripts")
     .update({"production_id": None})
     .eq("id", script_id).eq("production_id", production_id)
     .execute())
