# backend/services/production_location_service.py
# Account-level locations DIRECTORY (build-sequence step 3). NOT the creative
# scene-setting resolver in location_resolver.py.
"""Per-production location links. Production-authz scoped at the route layer;
this module trusts its caller has already passed require_production_role."""
from db.supabase_client import get_supabase_admin

_LOC_FIELDS = ("name", "address", "lat", "lng", "geocode_status", "permit_status",
               "parking_notes", "loadin_notes", "restrictions", "primary_contact_id")


def _location_owned_by(supabase, location_id, owner_id):
    res = (supabase.table("locations").select("*")
           .eq("id", location_id).eq("owner_id", owner_id).limit(1).execute())
    return res.data[0] if res.data else None


def link_location(production_id, location_id, owner_id, notes=None):
    supabase = get_supabase_admin()
    if not _location_owned_by(supabase, location_id, owner_id):
        return "not_owned"
    dup = (supabase.table("production_locations").select("id")
           .eq("production_id", production_id).eq("location_id", location_id)
           .limit(1).execute())
    if dup.data:
        return "exists"
    row = {"production_id": production_id, "location_id": location_id,
           "production_notes": notes}
    return supabase.table("production_locations").insert(row).execute().data[0]


def _link(supabase, link_id):
    res = (supabase.table("production_locations").select("*")
           .eq("id", link_id).limit(1).execute())
    return res.data[0] if res.data else None


def update_link(production_id, link_id, notes):
    supabase = get_supabase_admin()
    row = _link(supabase, link_id)
    if not row or row.get("production_id") != production_id:
        return "not_found"
    res = (supabase.table("production_locations").update({"production_notes": notes})
           .eq("id", link_id).execute())
    return res.data[0] if res.data else "not_found"


def unlink(production_id, link_id):
    supabase = get_supabase_admin()
    row = _link(supabase, link_id)
    if not row or row.get("production_id") != production_id:
        return "not_found"
    supabase.table("production_locations").delete().eq("id", link_id).execute()
    return "ok"


def list_for_production(production_id):
    supabase = get_supabase_admin()
    links = (supabase.table("production_locations").select("*")
             .eq("production_id", production_id).execute().data or [])
    if not links:
        return []
    loc_ids = list({l["location_id"] for l in links})
    locs = {l["id"]: l for l in (supabase.table("locations").select("*")
            .in_("id", loc_ids).execute().data or [])}
    contact_ids = [l.get("primary_contact_id") for l in locs.values() if l.get("primary_contact_id")]
    contacts = {}
    if contact_ids:
        contacts = {c["id"]: c for c in (supabase.table("contacts").select("id, name")
                    .in_("id", contact_ids).execute().data or [])}
    out = []
    for link in links:
        loc = locs.get(link["location_id"], {})
        row = {"link_id": link["id"], "location_id": link["location_id"],
               "production_notes": link.get("production_notes")}
        for f in _LOC_FIELDS:
            row[f] = loc.get(f)
        pc = loc.get("primary_contact_id")
        row["primary_contact_name"] = contacts.get(pc, {}).get("name") if pc else None
        out.append(row)
    return out
