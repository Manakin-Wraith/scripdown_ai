# backend/services/location_service.py
# Account-level locations DIRECTORY (build-sequence step 3). NOT the creative
# scene-setting resolver in location_resolver.py.
"""Owner-scoped locations directory. Every query filters owner_id == caller;
no script or production axis. Mirrors services/contact_service.py."""
import uuid as _uuid

from db.supabase_client import get_supabase_admin
from services import geocode_service

NOT_FOUND = object()

# Fields a caller may set directly. `geocode_status` is derived, never taken raw
# from create/update input except by internal helpers below.
FIELDS = ("name", "address", "lat", "lng", "primary_contact_id",
          "permit_status", "parking_notes", "loadin_notes", "restrictions", "notes")

PHOTO_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_PHOTO_BYTES = 5 * 1024 * 1024
PHOTO_BUCKET = "scripts"
SIGNED_URL_TTL = 3600


def _get(supabase, user_id, location_id):
    res = (supabase.table("locations").select("*")
           .eq("id", location_id).eq("owner_id", user_id).limit(1).execute())
    return res.data[0] if res.data else None


def _apply_geocode(fields, patch):
    """Fill lat/lng/geocode_status on `patch` from `fields`. Rules:
      - explicit lat AND lng supplied -> store them, status 'manual', no geocode
      - address present/changed, no explicit coords -> geocode; ok/failed
      - address explicitly blank -> null coords + status
    """
    has_addr = "address" in fields
    addr = (fields.get("address") or "").strip() if has_addr else None
    explicit = fields.get("lat") is not None and fields.get("lng") is not None
    if explicit:
        patch["lat"], patch["lng"] = fields["lat"], fields["lng"]
        patch["geocode_status"] = "manual"
        return
    if not has_addr:
        return
    if not addr:
        patch["lat"] = None
        patch["lng"] = None
        patch["geocode_status"] = None
        return
    hit = geocode_service.geocode(addr)
    if hit:
        patch["lat"], patch["lng"] = hit["lat"], hit["lng"]
        patch["geocode_status"] = "ok"
    else:
        patch["geocode_status"] = "failed"


def list_locations(user_id, q=None):
    query = get_supabase_admin().table("locations").select("*").eq("owner_id", user_id)
    if q:
        needle = q.strip().replace("%", "").replace(",", "")
        if needle:
            query = query.or_(f"name.ilike.%{needle}%,address.ilike.%{needle}%")
    return query.order("name").execute().data or []


def create_location(user_id, fields):
    supabase = get_supabase_admin()
    row = {"owner_id": user_id, "created_by": user_id,
           "name": (fields.get("name") or "").strip()}
    for f in FIELDS:
        if f != "name" and fields.get(f) is not None:
            row[f] = fields[f]
    _apply_geocode(fields, row)
    return supabase.table("locations").insert(row).execute().data[0]


def update_location(user_id, location_id, fields):
    supabase = get_supabase_admin()
    if not _get(supabase, user_id, location_id):
        return NOT_FOUND
    patch = {f: fields[f] for f in FIELDS if f in fields}
    if "name" in patch:
        patch["name"] = (patch["name"] or "").strip()
    _apply_geocode(fields, patch)
    if not patch:
        return _get(supabase, user_id, location_id)
    res = (supabase.table("locations").update(patch)
           .eq("id", location_id).eq("owner_id", user_id).execute())
    return res.data[0] if res.data else NOT_FOUND


def _linked_rows(supabase, location_id):
    return (supabase.table("production_locations").select("*")
            .eq("location_id", location_id).execute().data or [])


def location_usage(user_id, location_id):
    supabase = get_supabase_admin()
    links = _linked_rows(supabase, location_id)
    pids = list({l["production_id"] for l in links})
    if not pids:
        return []
    prods = (supabase.table("productions").select("id, title")
             .in_("id", pids).execute().data or [])
    return [{"production_id": p["id"], "production_title": p.get("title")} for p in prods]


def get_location_with_usage(user_id, location_id):
    supabase = get_supabase_admin()
    loc = _get(supabase, user_id, location_id)
    if not loc:
        return NOT_FOUND
    photos = (supabase.table("location_photos").select("*")
              .eq("location_id", location_id)
              .order("sort_order").order("created_at").execute().data or [])
    return {"location": loc,
            "photos": [_serialize_photo(p) for p in photos],
            "used_in": location_usage(user_id, location_id)}


def delete_location(user_id, location_id):
    supabase = get_supabase_admin()
    if not _get(supabase, user_id, location_id):
        return "not_found"
    if _linked_rows(supabase, location_id):
        return "in_use"
    supabase.table("locations").delete().eq("id", location_id).eq("owner_id", user_id).execute()
    return "ok"


# --- photos (Task 4 adds the tested surface; helper stub here) ---
def _serialize_photo(row):
    return {"id": row["id"], "caption": row.get("caption"),
            "sort_order": row.get("sort_order", 0), "url": _photo_url(row["storage_path"])}


def _photo_url(path):
    if not path:
        return None
    try:
        signed = (get_supabase_admin().storage.from_(PHOTO_BUCKET)
                  .create_signed_url(path, SIGNED_URL_TTL))
        return signed.get("signedURL") or signed.get("signed_url")
    except Exception:
        return None


class NotOwner(Exception):
    pass


def _require_owned(supabase, user_id, location_id):
    loc = _get(supabase, user_id, location_id)
    if not loc:
        raise NotOwner(location_id)
    return loc


def list_photos(user_id, location_id):
    supabase = get_supabase_admin()
    _require_owned(supabase, user_id, location_id)
    rows = (supabase.table("location_photos").select("*")
            .eq("location_id", location_id)
            .order("sort_order").order("created_at").execute().data or [])
    return [_serialize_photo(r) for r in rows]


def add_photo(user_id, location_id, file_bytes, content_type, caption=None):
    supabase = get_supabase_admin()
    _require_owned(supabase, user_id, location_id)
    ext = PHOTO_TYPES.get(content_type)
    if not ext:
        raise ValueError("Use a JPG, PNG, or WebP image.")
    if len(file_bytes) > MAX_PHOTO_BYTES:
        raise ValueError("That image is over 5 MB. Use a smaller file.")
    path = f"locations/{location_id}/{_uuid.uuid4().hex}.{ext}"
    supabase.storage.from_(PHOTO_BUCKET).upload(path, file_bytes, {"content-type": content_type})
    row = {"location_id": location_id, "storage_path": path, "caption": caption}
    return _serialize_photo(supabase.table("location_photos").insert(row).execute().data[0])


def delete_photo(user_id, location_id, photo_id):
    supabase = get_supabase_admin()
    _require_owned(supabase, user_id, location_id)
    res = (supabase.table("location_photos").select("*")
           .eq("id", photo_id).eq("location_id", location_id).limit(1).execute())
    if not res.data:
        return "not_found"
    try:
        supabase.storage.from_(PHOTO_BUCKET).remove([res.data[0]["storage_path"]])
    except Exception:
        pass
    supabase.table("location_photos").delete().eq("id", photo_id).execute()
    return "ok"
