"""Cast & Casting (v1) — persistence, breakdown-character aggregation,
serialization, and availability-conflict computation.

See docs/superpowers/specs/2026-08-27-cast-casting-v1-design.md.
"""
import uuid as _uuid
from datetime import date, datetime

from db.supabase_client import get_supabase_admin

UPDATABLE_FIELDS = {
    "character_name", "actor_name", "status", "contact_phone",
    "contact_email", "agent_contact", "headshot_path", "notes", "tier",
}
CONTACT_FIELDS = ("contact_phone", "contact_email", "agent_contact")
CONFLICT_STATUSES = ("booked", "offer")
VALID_STATUS = {"wishlist", "offer", "booked", "declined", "released"}
VALID_TIER = frozenset({"lead", "supporting", "featured", "background"})
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
    photos = (c.table("casting_photos").select("*")
              .in_("casting_id", ids).order("sort_order").order("created_at")
              .execute()).data or []
    photos_by_casting = {}
    for p in photos:
        photos_by_casting.setdefault(p["casting_id"], []).append(p)
    for r in rows:
        r["unavailability"] = by_casting.get(r["id"], [])
        r["photos"] = photos_by_casting.get(r["id"], [])
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
    row["photos"] = list_photos(casting_id)
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
    if "tier" in payload and payload["tier"] not in VALID_TIER:
        raise ValueError(f"invalid tier: {payload['tier']}")
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


VALID_PHOTO_KIND = frozenset({"headshot", "full_body", "other"})


def _photo_url(path):
    return _headshot_url(path)  # same bucket + signing


def list_photos(casting_id):
    rows = (_client().table("casting_photos").select("*")
            .eq("casting_id", casting_id)
            .order("sort_order").order("created_at").execute()).data or []
    return rows


def serialize_photo(row):
    return {
        "id": row["id"], "kind": row["kind"], "caption": row.get("caption"),
        "sort_order": row.get("sort_order", 0), "url": _photo_url(row["path"]),
    }


def store_photo(casting_id, script_id, kind, file_bytes, content_type):
    if kind not in VALID_PHOTO_KIND:
        raise ValueError(f"invalid photo kind: {kind}")
    ext = _HEADSHOT_TYPES.get(content_type)
    if not ext:
        raise ValueError("Use a JPG, PNG, or WebP image.")
    path = f"casting/{script_id}/{casting_id}/{_uuid.uuid4().hex}.{ext}"
    _client().storage.from_(HEADSHOT_BUCKET).upload(
        path, file_bytes, {"content-type": content_type})
    res = (_client().table("casting_photos").insert({
        "casting_id": casting_id, "path": path, "kind": kind,
    }).execute())
    return serialize_photo(res.data[0])


def delete_photo(photo_id):
    res = (_client().table("casting_photos").select("*")
           .eq("id", photo_id).limit(1).execute())
    if not res.data:
        return None
    row = res.data[0]
    try:
        _client().storage.from_(HEADSHOT_BUCKET).remove([row["path"]])
    except Exception:
        pass
    _client().table("casting_photos").delete().eq("id", photo_id).execute()
    return row


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
        "tier": row.get("tier") or "supporting",
        "headshot_path": row.get("headshot_path"),
        "headshot_url": _headshot_url(row.get("headshot_path")),
        "notes": row.get("notes"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "unavailability": row.get("unavailability", []),
        "photos": [serialize_photo(p) for p in (row.get("photos") or [])],
    }
    if include_contact:
        for f in CONTACT_FIELDS:
            out[f] = row.get(f)
    if breakdown_names is not None:
        out["orphaned"] = row["character_name"] not in breakdown_names
    return out


def active_schedule_id(script_id):
    rows = (_client().table("shooting_schedules").select("id, status, updated_at")
            .eq("script_id", script_id).eq("status", "active")
            .order("updated_at", desc=True).execute()).data or []
    return rows[0]["id"] if rows else None


def _alias_map(script_id):
    rows = (_client().table("character_aliases").select("alias, canonical_name")
            .eq("script_id", script_id).execute()).data or []
    return {norm_name(r["alias"]): norm_name(r["canonical_name"]) for r in rows}


TIER_CONFLICT = ("lead", "supporting", "featured")


def _suggested_day(days, current_day_id, scene_char_names, ranges_by_casting, casting_by_name):
    """Earliest dated day (not current) whose date is outside every relevant
    cast member's unavailability. `scene_char_names` = canonical names in the
    conflicting scene that have a booked/offer lead|supporting|featured row."""
    for d in sorted((x for x in days if x["id"] != current_day_id),
                    key=lambda x: str(x["shoot_date"])):
        ds = str(d["shoot_date"])
        clash = False
        for cname in scene_char_names:
            row = casting_by_name.get(cname)
            if not row:
                continue
            for rng in ranges_by_casting.get(row["id"], []):
                if str(rng["start_date"]) <= ds <= str(rng["end_date"]):
                    clash = True
                    break
            if clash:
                break
        if not clash:
            return {"shooting_day_id": d["id"], "day_number": d["day_number"],
                    "shoot_date": ds}
    return None


def compute_conflicts(script_id, schedule_id):
    c = _client()
    days = [d for d in (c.table("shooting_days").select("id, day_number, shoot_date")
            .eq("schedule_id", schedule_id).order("day_number").execute()).data or []
            if d.get("shoot_date")]
    if not days:
        return {"conflicts": [], "acknowledged": []}
    day_ids = [d["id"] for d in days]
    dps = (c.table("shooting_day_scenes").select("shooting_day_id, scene_id")
           .in_("shooting_day_id", day_ids).execute()).data or []
    scene_ids = list({p["scene_id"] for p in dps})
    if not scene_ids:
        return {"conflicts": [], "acknowledged": []}
    scenes = (c.table("scenes").select("id, characters")
              .in_("id", scene_ids).execute()).data or []
    amap = _alias_map(script_id)
    scene_chars = {
        s["id"]: {amap.get(norm_name(x), norm_name(x)) for x in (s.get("characters") or [])}
        for s in scenes
    }
    # day -> set of canonical character names
    day_chars = {}
    for p in dps:
        day_chars.setdefault(p["shooting_day_id"], set()).update(
            scene_chars.get(p["scene_id"], set())
        )

    casting_rows = [r for r in (c.table("casting")
                    .select("id, character_name, actor_name, status, tier")
                    .eq("script_id", script_id).execute()).data or []
                    if r.get("status") in CONFLICT_STATUSES
                    and (r.get("tier") or "supporting") in TIER_CONFLICT]
    if not casting_rows:
        return {"conflicts": [], "acknowledged": []}
    casting_by_name = {r["character_name"]: r for r in casting_rows}
    unavail = (c.table("casting_unavailability")
               .select("casting_id, start_date, end_date, reason")
               .in_("casting_id", [r["id"] for r in casting_rows]).execute()).data or []
    ranges_by_casting = {}
    for u in unavail:
        ranges_by_casting.setdefault(u["casting_id"], []).append(u)

    # day -> {scene_id: canonical character set} for the scenes on that day
    day_scene_ids = {}
    for p in dps:
        day_scene_ids.setdefault(p["shooting_day_id"], []).append(p["scene_id"])

    ack_rows = (c.table("shooting_day_scenes")
                .select("shooting_day_id, scene_id, conflict_ack, "
                        "conflict_ack_reason, conflict_ack_by, conflict_ack_at")
                .in_("shooting_day_id", day_ids).execute()).data or []
    ack_by_key = {(r["shooting_day_id"], r["scene_id"]): r for r in ack_rows}

    active, acknowledged = [], []
    for d in days:
        sd = str(d["shoot_date"])
        for cname in day_chars.get(d["id"], set()):
            row = casting_by_name.get(cname)
            if not row:
                continue
            matched = None
            for rng in ranges_by_casting.get(row["id"], []):
                if str(rng["start_date"]) <= sd <= str(rng["end_date"]):
                    matched = rng
                    break
            if not matched:
                continue
            scene_ids_for = [
                sid for sid in day_scene_ids.get(d["id"], [])
                if cname in scene_chars.get(sid, set())
            ]
            entry = {
                "shooting_day_id": d["id"],
                "day_number": d["day_number"],
                "shoot_date": sd,
                "character_name": cname,
                "actor_name": row.get("actor_name"),
                "reason": matched.get("reason"),
                "scene_ids": scene_ids_for,
            }
            ack_for = [ack_by_key.get((d["id"], sid)) for sid in scene_ids_for]
            if scene_ids_for and all(a and a.get("conflict_ack") for a in ack_for):
                a = ack_for[0]
                entry["ack_reason"] = a.get("conflict_ack_reason")
                entry["ack_by"] = a.get("conflict_ack_by")
                entry["ack_at"] = a.get("conflict_ack_at")
                acknowledged.append(entry)
            else:
                scene_char_names = set()
                for sid in scene_ids_for:
                    scene_char_names |= (scene_chars.get(sid, set())
                                         & set(casting_by_name))
                entry["suggested_day"] = _suggested_day(
                    days, d["id"], scene_char_names,
                    ranges_by_casting, casting_by_name)
                active.append(entry)
    return {"conflicts": active, "acknowledged": acknowledged}
