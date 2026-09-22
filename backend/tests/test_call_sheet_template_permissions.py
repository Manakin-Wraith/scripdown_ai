import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from middleware.production_authz import CAPABILITIES
from services.production_member_service import ROLE_PRESETS, apply_role_preset


def test_capability_registered():
    assert "can_edit_call_sheet_template" in CAPABILITIES


def test_coordinator_preset_contains_key_with_true():
    # Explicit key check: the DB column default (false) would mask a missing key.
    assert ROLE_PRESETS["coordinator"]["can_edit_call_sheet_template"] is True


def test_admin_and_viewer_presets():
    assert ROLE_PRESETS["admin"]["can_edit_call_sheet_template"] is True
    assert ROLE_PRESETS["viewer"]["can_edit_call_sheet_template"] is False


def test_override_can_revoke_from_coordinator():
    flags = apply_role_preset("coordinator", {"can_edit_call_sheet_template": False})
    assert flags["can_edit_call_sheet_template"] is False
