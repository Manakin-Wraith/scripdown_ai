"""Rename a character everywhere in the app without touching the script text.

A rename is a single-alias merge (old name -> new canonical name) plus a record of
the name as it appears in the script, so the UI can show "originally <name>".
Rewrites: scenes.characters, character refs on wardrobe/makeup items,
department_items, the casting row, and character_aliases.
"""
from db.supabase_client import get_supabase_admin


class RenameError(Exception):
    """Base class; `status` is the HTTP status the route should return."""
    status = 400


class CharacterNotFound(RenameError):
    status = 404


class NameTaken(RenameError):
    status = 409


def norm(name):
    return (name or "").strip().upper()


def _swap_character_refs(items, old, new):
    """Return (new_items, changed) with item['character'] == old repointed to new."""
    if not isinstance(items, list):
        return items, False
    out, changed = [], False
    for item in items:
        if isinstance(item, dict) and norm(item.get("character")) == old:
            item = {**item, "character": new}
            changed = True
        out.append(item)
    return out, changed


def _swap_characters(chars, old, new):
    """Replace old with new in a scene's character list, de-duplicating."""
    out, seen, changed = [], set(), False
    for c in chars or []:
        key = norm(c)
        if key == old:
            c, key, changed = new, new, True
        if key in seen:
            changed = True
            continue
        seen.add(key)
        out.append(c)
    return out, changed


def original_names(script_id, client=None):
    """canonical name -> name in the script, only where the two differ.

    Tolerant of the original_name column not existing yet (migration 062 not applied).
    """
    c = client or get_supabase_admin()
    try:
        rows = (c.table("character_aliases")
                .select("canonical_name, original_name")
                .eq("script_id", script_id).execute()).data or []
    except Exception:
        return {}
    out = {}
    for r in rows:
        orig, canon = norm(r.get("original_name")), norm(r.get("canonical_name"))
        if orig and orig != canon:
            out[canon] = orig
    return out


def rename_character(script_id, old_name, new_name, user_id, client=None):
    c = client or get_supabase_admin()
    old, new = norm(old_name), norm(new_name)
    if not old or not new:
        raise RenameError("Both the current and the new name are required")
    if old == new:
        raise RenameError("The new name is the same as the current name")

    scenes = (c.table("scenes").select("id, characters, wardrobe, makeup")
              .eq("script_id", script_id).execute()).data or []
    casting_old = (c.table("casting").select("id")
                   .eq("script_id", script_id).eq("character_name", old).execute()).data or []
    casting_new = (c.table("casting").select("id")
                   .eq("script_id", script_id).eq("character_name", new).execute()).data or []

    in_scenes = lambda name: any(  # noqa: E731
        norm(x) == name for s in scenes for x in (s.get("characters") or []))
    if not in_scenes(old) and not casting_old:
        raise CharacterNotFound(old)
    if in_scenes(new) or casting_new:
        raise NameTaken(new)

    # 1. Aliases first: if a later step fails, a retry still works.
    alias_rows = (c.table("character_aliases")
                  .select("alias, canonical_name, original_name")
                  .eq("script_id", script_id).execute()).data or []
    original = next(
        (norm(r["original_name"]) for r in alias_rows
         if norm(r.get("canonical_name")) == old and r.get("original_name")),
        old,
    )
    # Earlier aliases of the old name (merges and earlier renames) now point at the new name.
    c.table("character_aliases").update({"canonical_name": new}) \
        .eq("script_id", script_id).eq("canonical_name", old).execute()
    # The new name is a live name again, so it can't also be an alias of something.
    c.table("character_aliases").delete() \
        .eq("script_id", script_id).eq("alias", new).execute()
    c.table("character_aliases").upsert({
        "script_id": script_id, "canonical_name": new, "alias": old,
        "original_name": original, "merged_by": user_id,
    }, on_conflict="script_id,alias").execute()
    # Every rename row of this chain carries the same original name.
    c.table("character_aliases").update({"original_name": original}) \
        .eq("script_id", script_id).eq("canonical_name", new) \
        .not_.is_("original_name", "null").execute()

    # 2. Scenes (what breakdown, schedule, reports and PDFs read).
    scenes_updated = 0
    for s in scenes:
        patch = {}
        chars, changed = _swap_characters(s.get("characters"), old, new)
        if changed:
            patch["characters"] = chars
        for col in ("wardrobe", "makeup"):
            items, changed = _swap_character_refs(s.get(col), old, new)
            if changed:
                patch[col] = items
        if patch:
            c.table("scenes").update(patch).eq("id", s["id"]).execute()
            scenes_updated += 1

    # 3. User-added items and the casting row (call sheets follow casting_id).
    c.table("department_items").update({"item_name": new}) \
        .eq("script_id", script_id).eq("item_type", "characters") \
        .eq("item_name", old).execute()
    if casting_old:
        c.table("casting").update({"character_name": new}) \
            .eq("script_id", script_id).eq("character_name", old).execute()

    return {
        "character": new,
        "original_name": original if original != new else None,
        "scenes_updated": scenes_updated,
    }
