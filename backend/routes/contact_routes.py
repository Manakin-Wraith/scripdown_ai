"""Contacts directory HTTP routes. Logic in services/contact_service.py.
Owner-scoped: every route acts only on the caller's own contacts.
"""
from flask import Blueprint, request, jsonify

from middleware.auth import require_auth, get_user_id
from services import contact_service as svc
from services.contact_service import VALID_KINDS, VALID_RATE_UNITS

contacts_bp = Blueprint("contacts", __name__)


def _field_error(data):
    if data.get("kind") not in (None, *VALID_KINDS):
        return "kind must be 'person' or 'company'"
    if data.get("rate_unit") not in (None, *VALID_RATE_UNITS):
        return "rate_unit must be one of: day, week, flat"
    return None


@contacts_bp.route("/api/contacts", methods=["GET"])
@require_auth
def list_contacts():
    rows = svc.list_contacts(get_user_id(), request.args.get("q"), request.args.get("kind"))
    return jsonify({"contacts": rows})


@contacts_bp.route("/api/contacts", methods=["POST"])
@require_auth
def create_contact():
    data = request.get_json(silent=True) or {}
    if not (data.get("name") or "").strip():
        return jsonify({"error": "name is required"}), 400
    err = _field_error(data)
    if err:
        return jsonify({"error": err}), 400
    return jsonify({"contact": svc.create_contact(get_user_id(), data)}), 201


@contacts_bp.route("/api/contacts/<contact_id>", methods=["GET"])
@require_auth
def get_contact(contact_id):
    result = svc.get_contact_with_usage(get_user_id(), contact_id)
    if result is svc.NOT_FOUND:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify(result)


@contacts_bp.route("/api/contacts/<contact_id>", methods=["PATCH"])
@require_auth
def update_contact(contact_id):
    data = request.get_json(silent=True) or {}
    if "name" in data and not (data.get("name") or "").strip():
        return jsonify({"error": "name cannot be empty"}), 400
    err = _field_error(data)
    if err:
        return jsonify({"error": err}), 400
    result = svc.update_contact(get_user_id(), contact_id, data)
    if result is svc.NOT_FOUND:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify({"contact": result})


@contacts_bp.route("/api/contacts/<contact_id>", methods=["DELETE"])
@require_auth
def delete_contact(contact_id):
    user_id = get_user_id()
    outcome = svc.delete_contact(user_id, contact_id)
    if outcome == "not_found":
        return jsonify({"error": "Contact not found"}), 404
    if outcome == "in_use":
        return jsonify({"error": "Contact is assigned to crew",
                        "used_in": svc.contact_usage(user_id, contact_id)}), 409
    return jsonify({"success": True})
