"""Background casting groups — anonymous background booked by headcount.

See docs/superpowers/specs/2026-08-29-cast-tab-v2-design.md §3.2.
"""
from db.supabase_client import get_supabase_admin

VALID_STATUS = {"wishlist", "offer", "booked", "declined", "released"}
UPDATABLE = {"label", "headcount", "status", "day_rate", "notes"}


class GroupNotFound(Exception):
    """No casting_groups row for the given id."""


def _client():
    return get_supabase_admin()


def _scene_ids(group_id):
    rows = (_client().table("casting_group_scenes").select("scene_id")
            .eq("group_id", group_id).execute()).data or []
    return [r["scene_id"] for r in rows]


def _serialize(row, scene_ids=None):
    return {
        "id": row["id"],
        "script_id": row["script_id"],
        "label": row["label"],
        "headcount": row.get("headcount", 1),
        "status": row.get("status") or "wishlist",
        "day_rate": row.get("day_rate"),
        "notes": row.get("notes"),
        "scene_ids": _scene_ids(row["id"]) if scene_ids is None else scene_ids,
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


serialize_group = _serialize


def list_groups(script_id):
    rows = (_client().table("casting_groups").select("*")
            .eq("script_id", script_id).order("created_at").execute()).data or []
    if not rows:
        return []
    ids = [r["id"] for r in rows]
    links = (_client().table("casting_group_scenes").select("group_id, scene_id")
             .in_("group_id", ids).execute()).data or []
    by_group = {}
    for link in links:
        by_group.setdefault(link["group_id"], []).append(link["scene_id"])
    return [_serialize(r, scene_ids=by_group.get(r["id"], [])) for r in rows]


def get_group(group_id):
    res = (_client().table("casting_groups").select("*")
           .eq("id", group_id).limit(1).execute())
    return _serialize(res.data[0]) if res.data else None


def _validate(fields):
    if "headcount" in fields and (fields["headcount"] is None or int(fields["headcount"]) < 1):
        raise ValueError("headcount must be at least 1")
    if "status" in fields and fields["status"] not in VALID_STATUS:
        raise ValueError(f"invalid status: {fields['status']}")


def create_group(script_id, fields, user_id):
    label = (fields.get("label") or "").strip()
    if not label:
        raise ValueError("label is required")
    _validate(fields)
    payload = {"script_id": script_id, "label": label, "created_by": user_id}
    for k in ("headcount", "status", "day_rate", "notes"):
        if fields.get(k) is not None:
            payload[k] = fields[k]
    res = _client().table("casting_groups").insert(payload).execute()
    return _serialize(res.data[0])


def update_group(group_id, fields):
    payload = {k: v for k, v in fields.items() if k in UPDATABLE}
    if "label" in payload:
        payload["label"] = (payload["label"] or "").strip()
        if not payload["label"]:
            raise ValueError("label is required")
    _validate(payload)
    if not payload:
        grp = get_group(group_id)
        if not grp:
            raise GroupNotFound(group_id)
        return grp
    res = _client().table("casting_groups").update(payload).eq("id", group_id).execute()
    if not res.data:
        raise GroupNotFound(group_id)
    return get_group(group_id)


def delete_group(group_id):
    res = _client().table("casting_groups").delete().eq("id", group_id).execute()
    return res.data[0] if res.data else None


def set_group_scenes(group_id, scene_ids):
    grp = get_group(group_id)
    if not grp:
        raise GroupNotFound(group_id)
    scene_ids = list(dict.fromkeys(scene_ids or []))  # de-dupe, keep order
    if scene_ids:
        owned = (_client().table("scenes").select("id")
                 .eq("script_id", grp["script_id"]).in_("id", scene_ids).execute()).data or []
        owned_ids = {r["id"] for r in owned}
        bad = [s for s in scene_ids if s not in owned_ids]
        if bad:
            raise ValueError(f"scenes not in this script: {bad}")
    _client().table("casting_group_scenes").delete().eq("group_id", group_id).execute()
    if scene_ids:
        _client().table("casting_group_scenes").insert(
            [{"group_id": group_id, "scene_id": s} for s in scene_ids]).execute()
    return scene_ids
