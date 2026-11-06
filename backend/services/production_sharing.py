"""Production-level sharing of directory entries (contacts, locations).

Contacts and locations are personal address books (owner_id = the person who
added them). Inside a production they are pooled: the owner and every admin
(or member holding the relevant capability) can see and use each other's
entries for that production, and anything ATTACHED to it (crew contact, linked
location) is editable by all of them. Outside a production (the personal
Contacts/Locations pages) address books stay private.
"""


def production_circle_ids(supabase, production_id, flag):
    """User ids whose address books pool for this production: the owner plus
    every admin / member holding `flag`."""
    prod = (supabase.table("productions").select("owner_id")
            .eq("id", production_id).limit(1).execute().data or [])
    members = (supabase.table("production_members").select("*")
               .eq("production_id", production_id).execute().data or [])
    ids = {m["user_id"] for m in members
           if m.get("user_id") and (m.get("role") == "admin" or m.get(flag))}
    if prod and prod[0].get("owner_id"):
        ids.add(prod[0]["owner_id"])
    return ids


def pooled_owner_ids(supabase, user_id, production_id, flag):
    """The circle for `production_id`, but only if `user_id` is in it (else empty)."""
    circle = production_circle_ids(supabase, production_id, flag)
    return circle if user_id in circle else set()


def manageable_production_ids(supabase, user_id, flag):
    """Productions the user owns, or belongs to as an admin / with `flag` set."""
    if not user_id:
        return set()
    owned = (supabase.table("productions").select("id")
             .eq("owner_id", user_id).execute().data or [])
    members = (supabase.table("production_members").select("*")
               .eq("user_id", user_id).execute().data or [])
    pids = {p["id"] for p in owned}
    pids.update(m["production_id"] for m in members
                if m.get("role") == "admin" or m.get(flag))
    return pids


def _attached_ids(supabase, table, column, production_ids):
    if not production_ids:
        return set()
    rows = (supabase.table(table).select(column)
            .in_("production_id", list(production_ids)).execute().data or [])
    return {r[column] for r in rows if r.get(column)}


def shared_contact_ids(supabase, user_id, production_id=None):
    """Contact ids on crews of productions this user may manage crew for."""
    pids = manageable_production_ids(supabase, user_id, "can_edit_crew")
    if production_id is not None:
        pids &= {production_id}
    return _attached_ids(supabase, "production_crew", "contact_id", pids)


def shared_location_ids(supabase, user_id, production_id=None):
    """Location ids linked to productions this user may edit."""
    pids = manageable_production_ids(supabase, user_id, "can_edit_production")
    if production_id is not None:
        pids &= {production_id}
    return _attached_ids(supabase, "production_locations", "location_id", pids)
