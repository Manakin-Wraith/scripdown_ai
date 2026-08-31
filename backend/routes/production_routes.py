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


@production_bp.route("/api/productions/<production_id>", methods=["PATCH"])
@require_auth
def update_production(production_id):
    user_id = get_user_id()
    try:
        if not svc._get_production(svc.get_supabase_admin(), production_id):
            return jsonify({"error": "Production not found"}), 404
        if not svc._user_owns_production(production_id, user_id):
            return jsonify({"error": "Insufficient permissions"}), 403
        data = request.get_json(silent=True) or {}
        if "title" in data:
            data["title"] = (data.get("title") or "").strip()
            if not data["title"]:
                return jsonify({"error": "title cannot be empty"}), 400
        return jsonify({"production": svc.update_production(production_id, data)})
    except Exception as e:
        print(f"Error updating production: {e}")
        return jsonify({"error": str(e)}), 500


@production_bp.route("/api/productions/<production_id>", methods=["DELETE"])
@require_auth
def delete_production(production_id):
    user_id = get_user_id()
    try:
        if not svc._get_production(svc.get_supabase_admin(), production_id):
            return jsonify({"error": "Production not found"}), 404
        if not svc._user_owns_production(production_id, user_id):
            return jsonify({"error": "Insufficient permissions"}), 403
        # Explicitly null associated scripts (DB does this via ON DELETE SET
        # NULL too; doing it here keeps behavior identical under the mock).
        svc.get_supabase_admin().table("scripts").update(
            {"production_id": None}).eq("production_id", production_id).execute()
        svc.delete_production(production_id)
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error deleting production: {e}")
        return jsonify({"error": str(e)}), 500


@production_bp.route("/api/productions/<production_id>/scripts", methods=["POST"])
@require_auth
def add_script_to_production(production_id):
    user_id = get_user_id()
    try:
        if not svc._get_production(svc.get_supabase_admin(), production_id):
            return jsonify({"error": "Production not found"}), 404
        if not svc._user_owns_production(production_id, user_id):
            return jsonify({"error": "Insufficient permissions"}), 403
        script_id = (request.get_json(silent=True) or {}).get("script_id")
        if not script_id:
            return jsonify({"error": "script_id is required"}), 400
        outcome = svc.add_script(production_id, script_id, user_id)
        if outcome == "not_owned":
            return jsonify({"error": "You do not own that script"}), 403
        if outcome == "conflict":
            return jsonify({"error": "Script already belongs to a production"}), 409
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error adding script to production: {e}")
        return jsonify({"error": str(e)}), 500


@production_bp.route("/api/productions/<production_id>/scripts/<script_id>", methods=["DELETE"])
@require_auth
def remove_script_from_production(production_id, script_id):
    user_id = get_user_id()
    try:
        if not svc._get_production(svc.get_supabase_admin(), production_id):
            return jsonify({"error": "Production not found"}), 404
        if not svc._user_owns_production(production_id, user_id):
            return jsonify({"error": "Insufficient permissions"}), 403
        svc.remove_script(production_id, script_id)
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error removing script from production: {e}")
        return jsonify({"error": str(e)}), 500
