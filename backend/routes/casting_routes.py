"""Cast & Casting (v1) HTTP endpoints. See
docs/superpowers/specs/2026-08-27-cast-casting-v1-design.md §5."""
from flask import Blueprint, request, jsonify, g

from middleware.auth import require_auth, get_user_id
from middleware.authorization import (
    require_script_role, from_script, from_casting, from_casting_unavailability,
)
import services.casting_service as casting_service

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
