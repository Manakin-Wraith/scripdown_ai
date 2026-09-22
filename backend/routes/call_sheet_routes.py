"""Call sheet HTTP routes. Logic in services/call_sheet_service.py.
Gated by middleware.production_authz.require_production_role -- see
docs/superpowers/specs/2026-09-18-call-sheets-design.md's
"permission-system fork" section for why (production-role, not
script-role, despite the shooting_day anchor)."""
from flask import Blueprint, request, jsonify, g, Response

from middleware.auth import require_auth, get_user_id
from middleware.production_authz import (
    require_production_role, from_call_sheet_id, from_shooting_day_id,
)
from services import call_sheet_service as svc
from services import call_sheet_template_service as tpl

call_sheet_bp = Blueprint("call_sheet", __name__)


@call_sheet_bp.route("/api/shooting-days/<day_id>/call-sheet", methods=["POST"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_shooting_day_id)
def get_or_create_call_sheet(day_id):
    result = svc.get_or_create(day_id, get_user_id())
    if result == "no_production":
        return jsonify({"error": "Not found"}), 404
    return jsonify({"call_sheet": result})


@call_sheet_bp.route("/api/shooting-days/<day_id>/call-sheet", methods=["GET"])
@require_auth
@require_production_role(min_role="viewer", resolver=from_shooting_day_id)
def get_call_sheet_by_day(day_id):
    result = svc.get_by_day(day_id)
    if result is svc.NOT_FOUND:
        return jsonify({"error": "Call sheet not found"}), 404
    result = svc.redact_roster(result, g.production_access["can_view_sensitive"])
    return jsonify({"call_sheet": result})


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>", methods=["GET"])
@require_auth
@require_production_role(min_role="viewer", resolver=from_call_sheet_id)
def get_call_sheet(call_sheet_id):
    result = svc.get_call_sheet(call_sheet_id)
    if result is svc.NOT_FOUND:
        return jsonify({"error": "Call sheet not found"}), 404
    result = svc.redact_roster(result, g.production_access["can_view_sensitive"])
    return jsonify({"call_sheet": result})


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>", methods=["PATCH"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def update_call_sheet(call_sheet_id):
    data = request.get_json(silent=True) or {}
    try:
        result, ignored = svc.update_call_sheet_with_report(call_sheet_id, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if result is svc.NOT_FOUND:
        return jsonify({"error": "Call sheet not found"}), 404
    return jsonify({"call_sheet": result, "ignored_keys": ignored})


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/crew", methods=["POST"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def add_call_sheet_crew(call_sheet_id):
    data = request.get_json(silent=True) or {}
    crew_id = data.get("crew_id")
    if not crew_id:
        return jsonify({"error": "crew_id is required"}), 400
    result = svc.add_crew(call_sheet_id, crew_id, data.get("call_time"), data.get("notes"))
    if result == "not_found":
        return jsonify({"error": "Call sheet not found"}), 404
    if result == "cross_production":
        return jsonify({"error": "That crew member is not part of this production"}), 400
    result = svc.redact_roster({"crew": [result]}, g.production_access["can_view_sensitive"])["crew"][0]
    return jsonify({"crew": result}), 201


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/crew/<crew_id>", methods=["PATCH"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def update_call_sheet_crew(call_sheet_id, crew_id):
    data = request.get_json(silent=True) or {}
    result = svc.update_crew_call(call_sheet_id, crew_id, data)
    if result == "not_found":
        return jsonify({"error": "Call sheet or crew row not found"}), 404
    result = svc.redact_roster({"crew": [result]}, g.production_access["can_view_sensitive"])["crew"][0]
    return jsonify({"crew": result})


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/crew/<crew_id>", methods=["DELETE"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def remove_call_sheet_crew(call_sheet_id, crew_id):
    svc.remove_crew(call_sheet_id, crew_id)
    return jsonify({"success": True})


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/cast", methods=["POST"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def add_call_sheet_cast(call_sheet_id):
    data = request.get_json(silent=True) or {}
    casting_id = data.get("casting_id")
    if not casting_id:
        return jsonify({"error": "casting_id is required"}), 400
    result = svc.add_cast(call_sheet_id, casting_id, data.get("call_time"),
                          data.get("status_code"), data.get("notes"))
    if result == "not_found":
        return jsonify({"error": "Call sheet not found"}), 404
    if result == "cross_script":
        return jsonify({"error": "That cast member is not part of this shooting day's script"}), 400
    return jsonify({"cast": result}), 201


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/cast/<casting_id>", methods=["PATCH"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def update_call_sheet_cast(call_sheet_id, casting_id):
    data = request.get_json(silent=True) or {}
    result = svc.update_cast_call(call_sheet_id, casting_id, data)
    if result == "not_found":
        return jsonify({"error": "Call sheet or cast row not found"}), 404
    return jsonify({"cast": result})


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/cast/<casting_id>", methods=["DELETE"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def remove_call_sheet_cast(call_sheet_id, casting_id):
    svc.remove_cast(call_sheet_id, casting_id)
    return jsonify({"success": True})


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/locations", methods=["POST"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def add_call_sheet_location(call_sheet_id):
    data = request.get_json(silent=True) or {}
    location_id = data.get("location_id")
    if not location_id:
        return jsonify({"error": "location_id is required"}), 400
    result = svc.add_location(call_sheet_id, location_id, bool(data.get("is_primary")))
    if result == "not_found":
        return jsonify({"error": "Call sheet not found"}), 404
    if result == "cross_production":
        return jsonify({"error": "That location is not part of this production"}), 400
    return jsonify({"location": result}), 201


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/locations/<location_id>", methods=["DELETE"])
@require_auth
@require_production_role(capability="can_edit_call_sheets", resolver=from_call_sheet_id)
def remove_call_sheet_location(call_sheet_id, location_id):
    svc.remove_location(call_sheet_id, location_id)
    return jsonify({"success": True})


@call_sheet_bp.route("/api/call-sheets/<call_sheet_id>/pdf", methods=["GET"])
@require_auth
@require_production_role(min_role="viewer", resolver=from_call_sheet_id)
def download_call_sheet_pdf(call_sheet_id):
    pdf_bytes = svc.render_call_sheet_pdf(call_sheet_id)
    if pdf_bytes is svc.NOT_FOUND:
        return jsonify({"error": "Call sheet not found"}), 404
    return Response(pdf_bytes, mimetype="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=call_sheet.pdf"})


@call_sheet_bp.route("/api/productions/<production_id>/call-sheet-template", methods=["GET"])
@require_auth
@require_production_role(min_role="viewer")
def get_call_sheet_template(production_id):
    template = dict(tpl.get_template(production_id))
    # Lets the editor's "Reset to default" work without duplicating the default client-side.
    template["default_config"] = tpl.default_config()
    return jsonify({"template": template})


@call_sheet_bp.route("/api/productions/<production_id>/call-sheet-template", methods=["PUT"])
@require_auth
@require_production_role(capability="can_edit_call_sheet_template")
def put_call_sheet_template(production_id):
    data = request.get_json(silent=True) or {}
    try:
        saved = tpl.save_template(production_id, data.get("config"), get_user_id(),
                                  data.get("expected_updated_at"))
    except tpl.ConfigError as e:
        return jsonify({"error": "Invalid template", "details": e.errors}), 400
    except tpl.StaleTemplate:
        return jsonify({"error": "The template was changed by someone else",
                        "code": "stale_template"}), 409
    return jsonify({"template": saved})
