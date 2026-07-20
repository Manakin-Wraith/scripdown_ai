"""
Route-enforcement regression test.

Every /api/scripts/<script_id>/... route in routes/supabase_routes.py must
carry the require_script_role authorization decorator, except the explicit
whitelist of endpoints that are intentionally not single-script scoped
(list endpoint, upload/creation endpoint), or that are known/tracked
exceptions (see comments below).

Scope: this test currently checks only the `supabase` blueprint
(routes/supabase_routes.py), which is what teams-access-control-hardening
Task 4 converted. Other blueprints (reports, invite, analysis, script,
schedule, segments) have script_id-scoped routes of their own that are
NOT yet decorated with require_script_role -- that is out of scope for
Task 4 and is tracked by later tasks in
docs/superpowers/plans/2026-07-08-teams-access-control-hardening.md.
When those blueprints are converted, broaden BLUEPRINT_PREFIXES (or drop
the filter entirely) so this test covers them too.

This guards against a future route in supabase_routes.py being added (or
an existing one edited) without the authorization decorator being wired
up.
"""
import pytest

BLUEPRINT_PREFIXES = ("supabase.",)

# Not single-script scoped: list endpoint (filters by owner+membership
# itself) and the upload/creation endpoint (no script exists yet).
WHITELIST_ENDPOINTS = {"supabase.get_scripts", "supabase.upload_script"}

# Known script-scoped routes in supabase_routes.py that are NOT part of
# Task 4's conversion table and are therefore left untouched here:
#
# - merge_characters, rename_parent_location, rename_sub_location,
#   reassign_scene_location, merge_parent_locations, nest_location,
#   unnest_location, merge_locations, get_location_aliases,
#   get_location_suggestions, get_location_health: each already calls
#   the pre-existing inline `_user_can_access_script(script_id, user_id)`
#   helper for authorization. They are not decorator-based yet, so they
#   don't set `_authz_min_role`, but they are not unauthorized -- migrating
#   them to the decorator is left to a later task in the plan.
KNOWN_EXCEPTIONS = {
    "supabase.merge_characters",
    "supabase.rename_parent_location",
    "supabase.rename_sub_location",
    "supabase.reassign_scene_location",
    "supabase.merge_parent_locations",
    "supabase.nest_location",
    "supabase.unnest_location",
    "supabase.merge_locations",
    "supabase.get_location_aliases",
    "supabase.get_location_suggestions",
    "supabase.get_location_health",
}


@pytest.fixture
def flask_app():
    from app import app  # module-level Flask instance
    return app


def test_script_scoped_routes_enforced(flask_app):
    missing = []
    for rule in flask_app.url_map.iter_rules():
        if "script_id" not in rule.arguments:
            continue
        endpoint = rule.endpoint
        if not endpoint.startswith(BLUEPRINT_PREFIXES):
            continue
        if endpoint in WHITELIST_ENDPOINTS or endpoint in KNOWN_EXCEPTIONS:
            continue
        view = flask_app.view_functions[endpoint]
        if not getattr(view, "_authz_min_role", None):
            missing.append(endpoint)
    assert not missing, f"Unenforced script-scoped routes: {missing}"
