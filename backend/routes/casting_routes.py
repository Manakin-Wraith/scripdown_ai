"""Cast & Casting (v1) HTTP endpoints. See
docs/superpowers/specs/2026-08-27-cast-casting-v1-design.md §5."""
from flask import Blueprint, request, jsonify, g

from middleware.auth import require_auth, get_user_id
from middleware.authorization import (
    require_script_role, from_script, from_casting, from_casting_unavailability,
    from_casting_photo, from_casting_group,
)
import services.casting_service as casting_service
import services.casting_group_service as group_service

casting_bp = Blueprint("casting", __name__)


def _include_contact():
    return getattr(g, "script_role", None) in ("admin", "owner")


def _serialize_one(row):
    return casting_service.serialize(row, include_contact=_include_contact())


@casting_bp.route("/api/scripts/<script_id>/casting", methods=["GET"])
@require_auth
@require_script_role("viewer", resolver=from_script)
def list_casting(script_id):
    rows = casting_service.list_casting(script_id)
    counts = casting_service.breakdown_characters(script_id)
    names = set(counts) | {r["character_name"] for r in rows}
    inc = _include_contact()
    serialized = [
        casting_service.serialize(r, include_contact=inc, breakdown_names=set(counts))
        for r in rows
    ]
    casting_by_name = {r["character_name"]: r["id"] for r in rows}
    characters = [
        {"name": n, "scene_count": counts[n], "casting_id": casting_by_name.get(n)}
        for n in sorted(counts, key=lambda k: (-counts[k], k))
    ]
    return jsonify({"casting": serialized, "characters": characters}), 200


@casting_bp.route("/api/scripts/<script_id>/casting", methods=["POST"])
@require_auth
@require_script_role("admin", resolver=from_script)
def create_casting(script_id):
    data = request.get_json(silent=True) or {}
    try:
        row = casting_service.create_casting(script_id, data.get("character_name"), get_user_id())
    except casting_service.CastingConflict:
        return jsonify({"error": "Casting already exists for this character"}), 409
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"casting": _serialize_one(row)}), 201


@casting_bp.route("/api/casting/<casting_id>", methods=["PATCH"])
@require_auth
@require_script_role("admin", resolver=from_casting)
def update_casting(casting_id):
    data = request.get_json(silent=True) or {}
    try:
        row = casting_service.update_casting(casting_id, data)
    except casting_service.CastingNotFound:
        return jsonify({"error": "Not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"casting": _serialize_one(row)}), 200


@casting_bp.route("/api/casting/<casting_id>", methods=["DELETE"])
@require_auth
@require_script_role("admin", resolver=from_casting)
def delete_casting(casting_id):
    deleted = casting_service.delete_casting(casting_id)
    if deleted and deleted.get("headshot_path"):
        try:
            casting_service._client().storage.from_(
                casting_service.HEADSHOT_BUCKET
            ).remove([deleted["headshot_path"]])
        except Exception:
            pass
    return jsonify({"success": True}), 200


@casting_bp.route("/api/casting/<casting_id>/unavailability", methods=["POST"])
@require_auth
@require_script_role("admin", resolver=from_casting)
def add_unavailability(casting_id):
    data = request.get_json(silent=True) or {}
    start, end = data.get("start_date"), data.get("end_date")
    if not start or not end:
        return jsonify({"error": "start_date and end_date are required"}), 400
    try:
        row = casting_service.add_unavailability(casting_id, start, end, data.get("reason"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"unavailability": row}), 201


@casting_bp.route("/api/casting/unavailability/<unavail_id>", methods=["DELETE"])
@require_auth
@require_script_role("admin", resolver=from_casting_unavailability)
def delete_unavailability(unavail_id):
    casting_service.delete_unavailability(unavail_id)
    return jsonify({"success": True}), 200


@casting_bp.route("/api/casting/<casting_id>/headshot", methods=["POST"])
@require_auth
@require_script_role("admin", resolver=from_casting)
def upload_headshot(casting_id):
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400
    blob = file.read()
    if file.mimetype not in casting_service._HEADSHOT_TYPES:
        return jsonify({"error": "Use a JPG, PNG, or WebP image."}), 400
    if len(blob) > casting_service.MAX_HEADSHOT_BYTES:
        return jsonify({"error": "That image is over 5 MB. Use a smaller file."}), 413
    row = casting_service.get_casting(casting_id)
    if not row:
        return jsonify({"error": "Not found"}), 404
    try:
        path = casting_service.store_headshot(
            casting_id, row["script_id"], blob, file.mimetype
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    updated = casting_service.update_casting(casting_id, {"headshot_path": path})
    return jsonify({"casting": _serialize_one(updated)}), 200


@casting_bp.route("/api/casting/<casting_id>/photos", methods=["POST"])
@require_auth
@require_script_role("admin", resolver=from_casting)
def add_casting_photo(casting_id):
    file = request.files.get("file")
    kind = request.args.get("kind", "other")
    if not file:
        return jsonify({"error": "No file provided"}), 400
    blob = file.read()
    if file.mimetype not in casting_service._HEADSHOT_TYPES:
        return jsonify({"error": "Use a JPG, PNG, or WebP image."}), 400
    if len(blob) > casting_service.MAX_HEADSHOT_BYTES:
        return jsonify({"error": "That image is over 5 MB. Use a smaller file."}), 413
    row = casting_service.get_casting(casting_id)
    if not row:
        return jsonify({"error": "Not found"}), 404
    try:
        photo = casting_service.store_photo(
            casting_id, row["script_id"], kind, blob, file.mimetype)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"photo": photo}), 201


@casting_bp.route("/api/casting/photos/<photo_id>", methods=["DELETE"])
@require_auth
@require_script_role("admin", resolver=from_casting_photo)
def delete_casting_photo(photo_id):
    casting_service.delete_photo(photo_id)
    return jsonify({"success": True}), 200


@casting_bp.route("/api/scripts/<script_id>/casting/conflicts", methods=["GET"])
@require_auth
@require_script_role("viewer", resolver=from_script)
def casting_conflicts(script_id):
    schedule_id = request.args.get("schedule_id") or casting_service.active_schedule_id(script_id)
    if not schedule_id:
        return jsonify({"conflicts": [], "schedule_id": None}), 200
    owner = casting_service._client().table("shooting_schedules").select("script_id") \
        .eq("id", schedule_id).limit(1).execute()
    if not owner.data or owner.data[0]["script_id"] != script_id:
        return jsonify({"error": "Schedule not found for this script"}), 404
    conflicts = casting_service.compute_conflicts(script_id, schedule_id)
    return jsonify({"conflicts": conflicts, "schedule_id": schedule_id}), 200


# --- Background casting groups -------------------------------------------------


@casting_bp.route("/api/scripts/<script_id>/casting-groups", methods=["GET"])
@require_auth
@require_script_role("viewer", resolver=from_script)
def list_casting_groups(script_id):
    return jsonify({"groups": group_service.list_groups(script_id)}), 200


@casting_bp.route("/api/scripts/<script_id>/casting-groups", methods=["POST"])
@require_auth
@require_script_role("admin", resolver=from_script)
def create_casting_group(script_id):
    data = request.get_json(silent=True) or {}
    try:
        row = group_service.create_group(script_id, data, get_user_id())
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"group": row}), 201


@casting_bp.route("/api/casting-groups/<group_id>", methods=["PATCH"])
@require_auth
@require_script_role("admin", resolver=from_casting_group)
def update_casting_group(group_id):
    data = request.get_json(silent=True) or {}
    try:
        row = group_service.update_group(group_id, data)
    except group_service.GroupNotFound:
        return jsonify({"error": "Not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"group": row}), 200


@casting_bp.route("/api/casting-groups/<group_id>", methods=["DELETE"])
@require_auth
@require_script_role("admin", resolver=from_casting_group)
def delete_casting_group(group_id):
    group_service.delete_group(group_id)
    return jsonify({"success": True}), 200


@casting_bp.route("/api/casting-groups/<group_id>/scenes", methods=["PUT"])
@require_auth
@require_script_role("admin", resolver=from_casting_group)
def set_casting_group_scenes(group_id):
    data = request.get_json(silent=True) or {}
    try:
        ids = group_service.set_group_scenes(group_id, data.get("scene_ids") or [])
    except group_service.GroupNotFound:
        return jsonify({"error": "Not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"scene_ids": ids}), 200
