"""Cast & Casting (v1) — persistence, breakdown-character aggregation,
serialization, and availability-conflict computation.

See docs/superpowers/specs/2026-08-27-cast-casting-v1-design.md.
"""
from datetime import date, datetime

from db.supabase_client import get_supabase_admin

UPDATABLE_FIELDS = {
    "character_name", "actor_name", "status", "contact_phone",
    "contact_email", "agent_contact", "headshot_path", "notes",
}
CONTACT_FIELDS = ("contact_phone", "contact_email", "agent_contact")
CONFLICT_STATUSES = ("booked", "offer")
VALID_STATUS = {"wishlist", "offer", "booked", "declined", "released"}
HEADSHOT_BUCKET = "scripts"
SIGNED_URL_TTL = 3600  # seconds


class CastingConflict(Exception):
    """A casting row already exists for this (script_id, character_name)."""


class CastingNotFound(Exception):
    """No casting row for the given id."""


def _client():
    return get_supabase_admin()


def norm_name(name):
    return (name or "").strip().upper()


def breakdown_characters(script_id):
    """canonical character name -> scene count, resolved through character_aliases."""
    c = _client()
    aliases = (c.table("character_aliases")
               .select("alias, canonical_name").eq("script_id", script_id).execute())
    alias_map = {norm_name(r["alias"]): norm_name(r["canonical_name"])
                 for r in (aliases.data or [])}
    scenes = (c.table("scenes").select("id, characters")
              .eq("script_id", script_id).execute())
    counts = {}
    for scene in (scenes.data or []):
        seen = set()
        for raw in (scene.get("characters") or []):
            canon = alias_map.get(norm_name(raw), norm_name(raw))
            if not canon or canon in seen:
                continue
            seen.add(canon)
            counts[canon] = counts.get(canon, 0) + 1
    return counts


def list_casting(script_id):
    c = _client()
    rows = (c.table("casting").select("*")
            .eq("script_id", script_id).order("character_name").execute()).data or []
    if not rows:
        return []
    ids = [r["id"] for r in rows]
    unavail = (c.table("casting_unavailability").select("*")
               .in_("casting_id", ids).order("start_date").execute()).data or []
    by_casting = {}
    for u in unavail:
        by_casting.setdefault(u["casting_id"], []).append(u)
    for r in rows:
        r["unavailability"] = by_casting.get(r["id"], [])
    return rows


def get_casting(casting_id):
    c = _client()
    res = (c.table("casting").select("*").eq("id", casting_id).limit(1).execute())
    if not res.data:
        return None
    row = res.data[0]
    unavail = (c.table("casting_unavailability").select("*")
               .eq("casting_id", casting_id).order("start_date").execute()).data or []
    row["unavailability"] = unavail
    return row


def create_casting(script_id, character_name, user_id):
    name = norm_name(character_name)
    if not name:
        raise ValueError("character_name is required")
    c = _client()
    existing = (c.table("casting").select("id")
                .eq("script_id", script_id).eq("character_name", name).limit(1).execute())
    if existing.data:
        raise CastingConflict(name)
    res = (c.table("casting").insert({
        "script_id": script_id, "character_name": name,
        "status": "wishlist", "created_by": user_id,
    }).execute())
    row = res.data[0]
    row["unavailability"] = []
    return row


def update_casting(casting_id, fields):
    payload = {k: v for k, v in fields.items() if k in UPDATABLE_FIELDS}
    if "character_name" in payload:
        payload["character_name"] = norm_name(payload["character_name"])
    if "status" in payload and payload["status"] not in VALID_STATUS:
        raise ValueError(f"invalid status: {payload['status']}")
    if not payload:
        return get_casting(casting_id)
    c = _client()
    res = (c.table("casting").update(payload).eq("id", casting_id).execute())
    if not res.data:
        raise CastingNotFound(casting_id)
    return get_casting(casting_id)


def delete_casting(casting_id):
    c = _client()
    res = (c.table("casting").delete().eq("id", casting_id).execute())
    return res.data[0] if res.data else None


def add_unavailability(casting_id, start_date, end_date, reason):
    s, e = str(start_date), str(end_date)
    if e < s:
        raise ValueError("end_date must be on or after start_date")
    c = _client()
    res = (c.table("casting_unavailability").insert({
        "casting_id": casting_id, "start_date": s, "end_date": e,
        "reason": (reason or None),
    }).execute())
    return res.data[0]


def delete_unavailability(unavail_id):
    _client().table("casting_unavailability").delete().eq("id", unavail_id).execute()


def _headshot_url(path):
    if not path:
        return None
    try:
        signed = (_client().storage.from_(HEADSHOT_BUCKET)
                  .create_signed_url(path, SIGNED_URL_TTL))
        return signed.get("signedURL") or signed.get("signed_url")
    except Exception:
        return None


_HEADSHOT_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_HEADSHOT_BYTES = 5 * 1024 * 1024


def store_headshot(casting_id, script_id, file_bytes, content_type):
    ext = _HEADSHOT_TYPES.get(content_type)
    if not ext:
        raise ValueError("Use a JPG, PNG, or WebP image.")
    path = f"casting/{script_id}/{casting_id}.{ext}"
    _client().storage.from_(HEADSHOT_BUCKET).upload(
        path, file_bytes,
        {"content-type": content_type, "upsert": "true"},
    )
    return path


def serialize(row, *, include_contact, breakdown_names=None):
    out = {
        "id": row["id"],
        "script_id": row["script_id"],
        "character_name": row["character_name"],
        "actor_name": row.get("actor_name"),
        "status": row.get("status") or "wishlist",
        "headshot_path": row.get("headshot_path"),
        "headshot_url": _headshot_url(row.get("headshot_path")),
        "notes": row.get("notes"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "unavailability": row.get("unavailability", []),
    }
    if include_contact:
        for f in CONTACT_FIELDS:
            out[f] = row.get(f)
    if breakdown_names is not None:
        out["orphaned"] = row["character_name"] not in breakdown_names
    return out
