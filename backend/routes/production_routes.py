"""
Production HTTP routes. Logic lives in services/production_service.py.
Owner-scoped list/write; GET-one also serves team members with a script
role inside the production (see production_service.get_production_for_viewer).
"""
from flask import Blueprint, request, jsonify

from middleware.auth import require_auth, get_user_id
from services import production_service as svc

production_bp = Blueprint("production", __name__)


@production_bp.route("/api/productions", methods=["POST"])
@require_auth
def create_production():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    data["title"] = title
    try:
        result = svc.create_production(get_user_id(), data)
        return jsonify(result), 201
    except Exception as e:
        print(f"Error creating production: {e}")
        return jsonify({"error": str(e)}), 500


@production_bp.route("/api/productions", methods=["GET"])
@require_auth
def list_productions():
    try:
        return jsonify({"productions": svc.list_productions(get_user_id())})
    except Exception as e:
        print(f"Error listing productions: {e}")
        return jsonify({"error": str(e)}), 500


@production_bp.route("/api/productions/<production_id>", methods=["GET"])
@require_auth
def get_production(production_id):
    try:
        result = svc.get_production_for_viewer(production_id, get_user_id())
        if result is svc.NOT_FOUND:
            return jsonify({"error": "Production not found"}), 404
        if result is None:
            return jsonify({"error": "Insufficient permissions"}), 403
        return jsonify(result)
    except Exception as e:
        print(f"Error getting production: {e}")
        return jsonify({"error": str(e)}), 500
