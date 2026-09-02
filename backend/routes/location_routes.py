# backend/routes/location_routes.py
# Account-level locations DIRECTORY (build-sequence step 3). NOT the creative
# scene-setting resolver in location_resolver.py.
"""Locations directory HTTP routes. Logic in services/location_service.py.
Owner-scoped: every route acts only on the caller's own locations."""
from flask import Blueprint, request, jsonify

from middleware.auth import require_auth, get_user_id
from services import location_service as svc
from services import geocode_service

locations_bp = Blueprint("locations", __name__)


@locations_bp.route("/api/locations", methods=["GET"])
@require_auth
def list_locations():
    return jsonify({"locations": svc.list_locations(get_user_id(), request.args.get("q"))})


@locations_bp.route("/api/locations", methods=["POST"])
@require_auth
def create_location():
    data = request.get_json(silent=True) or {}
    if not (data.get("name") or "").strip():
        return jsonify({"error": "name is required"}), 400
    return jsonify({"location": svc.create_location(get_user_id(), data)}), 201


@locations_bp.route("/api/locations/<location_id>", methods=["GET"])
@require_auth
def get_location(location_id):
    result = svc.get_location_with_usage(get_user_id(), location_id)
    if result is svc.NOT_FOUND:
        return jsonify({"error": "Location not found"}), 404
    return jsonify(result)


@locations_bp.route("/api/locations/<location_id>", methods=["PATCH"])
@require_auth
def update_location(location_id):
    data = request.get_json(silent=True) or {}
    if "name" in data and not (data.get("name") or "").strip():
        return jsonify({"error": "name cannot be empty"}), 400
    result = svc.update_location(get_user_id(), location_id, data)
    if result is svc.NOT_FOUND:
        return jsonify({"error": "Location not found"}), 404
    return jsonify({"location": result})


@locations_bp.route("/api/locations/<location_id>", methods=["DELETE"])
@require_auth
def delete_location(location_id):
    user_id = get_user_id()
    outcome = svc.delete_location(user_id, location_id)
    if outcome == "not_found":
        return jsonify({"error": "Location not found"}), 404
    if outcome == "in_use":
        return jsonify({"error": "Location is linked to productions",
                        "used_in": svc.location_usage(user_id, location_id)}), 409
    return jsonify({"success": True})


@locations_bp.route("/api/locations/<location_id>/photos", methods=["POST"])
@require_auth
def add_location_photo(location_id):
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400
    blob = file.read()
    try:
        photo = svc.add_photo(get_user_id(), location_id, blob, file.mimetype,
                              caption=request.args.get("caption"))
    except svc.NotOwner:
        return jsonify({"error": "Location not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"photo": photo}), 201


@locations_bp.route("/api/locations/<location_id>/photos/<photo_id>", methods=["DELETE"])
@require_auth
def delete_location_photo(location_id, photo_id):
    try:
        outcome = svc.delete_photo(get_user_id(), location_id, photo_id)
    except svc.NotOwner:
        return jsonify({"error": "Location not found"}), 404
    if outcome == "not_found":
        return jsonify({"error": "Photo not found"}), 404
    return jsonify({"success": True})


@locations_bp.route("/api/locations/geocode", methods=["POST"])
@require_auth
def geocode_address():
    data = request.get_json(silent=True) or {}
    hit = geocode_service.geocode(data.get("address"))
    return jsonify(hit or {"lat": None, "lng": None})
