"""
Production HTTP routes. Logic lives in services/production_service.py.
Owner-scoped list/write; GET-one also serves team members with a script
role inside the production (see production_service.get_production_for_viewer).
"""
from flask import Blueprint, request, jsonify, g

from middleware.auth import require_auth, get_user_id
from middleware.production_authz import (
    require_production_role, from_crew_id, from_member_id, from_production_invite_id,
    from_production_location_id,
)
from services import production_service as svc
from services import production_crew_service as crew_svc
from services import production_member_service as member_svc
from services import production_location_service as ploc_svc
from services.production_service import VALID_STATUSES

production_bp = Blueprint("production", __name__)

# Error codes the frontend switches on get echoed as a machine-readable `code`;
# the service already carries the HTTP status.
_MEMBER_ERR_WITH_CODE = {'rank_denied', 'tier_2_required', 'no_seats_available',
                         'duplicate_member', 'duplicate_invite', 'bad_role',
                         'cannot_target_owner'}


def _member_error(result):
    _, code, status = result
    body = {'error': code}
    if code in _MEMBER_ERR_WITH_CODE:
        body['code'] = code
    return jsonify(body), status


def _invalid_status(data):
    """Return an error string if 'status' is present but not an allowed value."""
    if "status" in data and data.get("status") is not None:
        if data["status"] not in VALID_STATUSES:
            return "status must be one of: " + ", ".join(sorted(VALID_STATUSES))
    return None


@production_bp.route("/api/productions", methods=["POST"])
@require_auth
def create_production():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    data["title"] = title
    status_err = _invalid_status(data)
    if status_err:
        return jsonify({"error": status_err}), 400
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
@require_production_role(capability="can_edit_production")
def update_production(production_id):
    try:
        data = request.get_json(silent=True) or {}
        if "title" in data:
            data["title"] = (data.get("title") or "").strip()
            if not data["title"]:
                return jsonify({"error": "title cannot be empty"}), 400
        status_err = _invalid_status(data)
        if status_err:
            return jsonify({"error": status_err}), 400
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
        svc.get_supabase_admin().table("production_crew").delete().eq(
            "production_id", production_id).execute()
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


@production_bp.route("/api/productions/<production_id>/crew", methods=["GET"])
@require_auth
@require_production_role(min_role="viewer")
def list_production_crew(production_id):
    return jsonify({"crew": crew_svc.list_crew(
        production_id, can_view_sensitive=g.production_access["can_view_sensitive"])})


@production_bp.route("/api/productions/<production_id>/crew", methods=["POST"])
@require_auth
@require_production_role(capability="can_edit_crew")
def add_production_crew(production_id):
    data = request.get_json(silent=True) or {}
    try:
        result = crew_svc.add_crew(
            production_id, get_user_id(), data,
            can_view_sensitive=g.production_access["can_view_sensitive"])
        if result == "bad_contact":
            return jsonify({"error": "contact_id must be one of your contacts"}), 400
        if result == "bad_department":
            return jsonify({"error": "Unknown department_code"}), 400
        if result == "bad_rate_unit":
            return jsonify({"error": "job_rate_unit must be one of: day, week, flat"}), 400
        if result == "bad_dates":
            return jsonify({"error": "end_date must be on or after start_date"}), 400
        return jsonify({"crew": result}), 201
    except Exception as e:
        print(f"Error adding production crew: {e}")
        return jsonify({"error": str(e)}), 500


@production_bp.route("/api/productions/<production_id>/crew/<crew_id>", methods=["PATCH"])
@require_auth
@require_production_role(capability="can_edit_crew", resolver=from_crew_id)
def update_production_crew(production_id, crew_id):
    data = request.get_json(silent=True) or {}
    try:
        result = crew_svc.update_crew(
            production_id, crew_id, data,
            can_view_sensitive=g.production_access["can_view_sensitive"])
        if result == "not_found":
            return jsonify({"error": "Crew assignment not found"}), 404
        if result == "bad_department":
            return jsonify({"error": "Unknown department_code"}), 400
        if result == "bad_rate_unit":
            return jsonify({"error": "job_rate_unit must be one of: day, week, flat"}), 400
        if result == "bad_dates":
            return jsonify({"error": "end_date must be on or after start_date"}), 400
        return jsonify({"crew": result})
    except Exception as e:
        print(f"Error updating production crew: {e}")
        return jsonify({"error": str(e)}), 500


@production_bp.route("/api/productions/<production_id>/crew/import", methods=["POST"])
@require_auth
@require_production_role(capability="can_edit_crew")
def import_production_crew(production_id):
    upload = request.files.get("file")
    if not upload:
        return jsonify({"error": "file is required"}), 400
    raw = upload.read()
    if len(raw) > 1_000_000:
        return jsonify({"error": "File too large (max ~1 MB)"}), 400
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return jsonify({"error": "File must be UTF-8 CSV"}), 400
    result = crew_svc.import_crew_csv(
        production_id, get_user_id(), text,
        can_view_sensitive=g.production_access["can_view_sensitive"])
    if isinstance(result, tuple) and result[0] == "fatal":
        return jsonify({"error": result[1]}), 400
    return jsonify(result)


@production_bp.route("/api/productions/<production_id>/crew/<crew_id>", methods=["DELETE"])
@require_auth
@require_production_role(capability="can_edit_crew", resolver=from_crew_id)
def remove_production_crew(production_id, crew_id):
    crew_svc.remove_crew(production_id, crew_id)
    return jsonify({"success": True})


@production_bp.route("/api/productions/<production_id>/locations", methods=["GET"])
@require_auth
@require_production_role(min_role="viewer")
def list_production_locations(production_id):
    return jsonify({"locations": ploc_svc.list_for_production(production_id)})


@production_bp.route("/api/productions/<production_id>/locations", methods=["POST"])
@require_auth
@require_production_role(capability="can_edit_production")
def link_production_location(production_id):
    data = request.get_json(silent=True) or {}
    location_id = (data.get("location_id") or "").strip()
    if not location_id:
        return jsonify({"error": "location_id is required"}), 400
    owner_id = svc.get_production_owner_id(production_id)
    result = ploc_svc.link_location(production_id, location_id, owner_id,
                                    notes=data.get("production_notes"))
    if result == "not_owned":
        return jsonify({"error": "That location is not in this production owner's directory"}), 404
    if result == "exists":
        return jsonify({"error": "That location is already linked to this production"}), 409
    return jsonify({"location": result}), 201


@production_bp.route("/api/productions/<production_id>/locations/<link_id>", methods=["PATCH"])
@require_auth
@require_production_role(capability="can_edit_production", resolver=from_production_location_id)
def update_production_location(production_id, link_id):
    data = request.get_json(silent=True) or {}
    result = ploc_svc.update_link(production_id, link_id, data.get("production_notes"))
    if result == "not_found":
        return jsonify({"error": "Not found"}), 404
    return jsonify({"location": result})


@production_bp.route("/api/productions/<production_id>/locations/<link_id>", methods=["DELETE"])
@require_auth
@require_production_role(capability="can_edit_production", resolver=from_production_location_id)
def unlink_production_location(production_id, link_id):
    if ploc_svc.unlink(production_id, link_id) == "not_found":
        return jsonify({"error": "Not found"}), 404
    return jsonify({"success": True})


@production_bp.route("/api/productions/<production_id>/members", methods=["GET"])
@require_auth
@require_production_role(min_role="viewer")
def list_production_members(production_id):
    return jsonify(member_svc.list_members_and_invites(production_id))


@production_bp.route("/api/productions/<production_id>/members", methods=["POST"])
@require_auth
@require_production_role(capability="can_manage_members")
def add_production_member(production_id):
    data = request.get_json(silent=True) or {}
    result = member_svc.add_member(
        production_id, get_user_id(), g.production_access, data)
    if isinstance(result, tuple):
        return _member_error(result)
    return jsonify(result), 201


@production_bp.route("/api/productions/<production_id>/members/<member_id>", methods=["PATCH"])
@require_auth
@require_production_role(capability="can_manage_members", resolver=from_member_id)
def update_production_member(production_id, member_id):
    data = request.get_json(silent=True) or {}
    result = member_svc.update_member(
        production_id, member_id, get_user_id(), g.production_access, data)
    if isinstance(result, tuple):
        return _member_error(result)
    return jsonify(result)


@production_bp.route("/api/productions/<production_id>/members/<member_id>", methods=["DELETE"])
@require_auth
@require_production_role(capability="can_manage_members")
def remove_production_member(production_id, member_id):
    # Resolves via production_id (not the member row) so deleting an already-
    # absent member is a 200 no-op rather than a 404.
    result = member_svc.remove_member(
        production_id, member_id, get_user_id(), g.production_access)
    if isinstance(result, tuple):
        return _member_error(result)
    return jsonify({"success": True})


# --- Invite lifecycle ---------------------------------------------------------
# The token/<token> routes stay above the <invite_id> route for clarity.

@production_bp.route("/api/production-invites/token/<token>", methods=["GET"])
def get_production_invite(token):
    # PUBLIC — powers the invite-accept landing page for logged-out users.
    info = member_svc.get_invite_by_token(token)
    if not info:
        return jsonify({"error": "Invite not found", "code": "not_found"}), 404
    return jsonify(info)


@production_bp.route("/api/production-invites/token/<token>/accept", methods=["POST"])
@require_auth
def accept_production_invite(token):
    user_email = (g.current_user or {}).get("email", "")
    result = member_svc.accept_invite(token, get_user_id(), user_email)
    if isinstance(result, tuple):
        _, code, status = result
        return jsonify({"error": code, "code": code}), status
    return jsonify(result)


@production_bp.route("/api/production-invites/<invite_id>", methods=["DELETE"])
@require_auth
@require_production_role(capability="can_manage_members", resolver=from_production_invite_id)
def revoke_production_invite(invite_id):
    member_svc.revoke_invite(invite_id, g.resolved_production_id)
    return jsonify({"success": True})
