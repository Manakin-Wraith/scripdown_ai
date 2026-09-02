"""
Route-enforcement regression test.

Every /api/scripts/<script_id>/... route in routes/supabase_routes.py must
carry the require_script_role authorization decorator, except the explicit
whitelist of endpoints that are intentionally not single-script scoped
(list endpoint, upload/creation endpoint), or that are known/tracked
exceptions (see comments below).

This also covers routes keyed by a CHILD resource instead of script_id
directly -- scene_id, note_id, item_id in the URL path -- which Task 5
converted using resolvers (from_scene, from_note, from_item) that look up
the parent script_id from the database. These routes carry the same
require_script_role decorator and the same _authz_min_role marker, so
they're checked identically; only the URL-argument name differs.

Scope: this test checks the `supabase` blueprint (routes/supabase_routes.py,
Tasks 4-5), the `schedule` blueprint (routes/schedule_routes.py, Task 6),
the `reports` blueprint (routes/report_routes.py, Task 7), and the `invite`
blueprint (routes/invite_routes.py, Task 11) -- the four blueprints the
teams-access-control-hardening plan converted to the decorator.
Other blueprints (analysis, script, segments) have script_id-scoped routes
of their own that are NOT yet decorated with require_script_role -- that is
out of scope for this plan and is tracked separately in
docs/superpowers/plans/2026-07-08-teams-access-control-hardening.md.
When those blueprints are converted, broaden BLUEPRINT_PREFIXES (or drop
the filter entirely) so this test covers them too.

This guards against a future route in supabase_routes.py being added (or
an existing one edited) without the authorization decorator being wired
up.
"""
import pytest

BLUEPRINT_PREFIXES = ("supabase.", "reports.", "schedule.", "invite.", "series.")

# URL rule arguments that indicate a route is scoped to a single script,
# either directly (script_id) or via a child resource whose parent script
# is resolved by a resolver function. schedule_id/day_id/from_day_id come
# from schedule_routes.py (Task 6); report_id/preset_id from
# report_routes.py (Task 7); member_id from invite_routes.py (Task 11).
SCOPED_ARG_NAMES = {
    "script_id", "scene_id", "note_id", "item_id",
    "schedule_id", "day_id", "from_day_id",
    "report_id", "preset_id",
    "member_id",
}

# Not single-script scoped: list endpoint (filters by owner+membership
# itself) and the upload/creation endpoint (no script exists yet).
#
# invite.get_my_membership is self-scoped like supabase.get_scripts: it
# only ever returns the CALLING user's own membership/role on the script
# (looked up by .eq('user_id', user_id), or an owner check against the
# caller's own id) -- it never exposes another user's data, so a min-role
# gate isn't meaningful here (the "role" being read IS the answer to the
# authorization question).
WHITELIST_ENDPOINTS = {
    "supabase.get_scripts", "supabase.upload_script",
    "invite.get_my_membership",
}

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
        if not (SCOPED_ARG_NAMES & rule.arguments):
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


def test_shared_report_routes_are_public(flask_app):
    # Endpoint names are blueprint-qualified ("reports.<view_func_name>")
    # since report_bp = Blueprint('reports', __name__); bare names would
    # never match any rule and this test would pass vacuously.
    public = {
        "reports.get_shared_report",
        "reports.download_shared_pdf",
        "reports.get_shared_printable",
    }
    matched = set()
    for rule in flask_app.url_map.iter_rules():
        if rule.endpoint in public:
            matched.add(rule.endpoint)
            view = flask_app.view_functions[rule.endpoint]
            assert not getattr(view, "_authz_min_role", None), \
                f"{rule.endpoint} must stay public"
    assert matched == public, f"Expected shared routes not found: {public - matched}"


def test_production_scoped_routes_carry_authz_marker():
    """Every production_bp route keyed to a production (directly or via a
    child resource) must carry require_production_role — i.e. expose an
    _authz_min_role or _authz_capability marker on its view function."""
    from routes.production_routes import production_bp
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(production_bp)

    # Routes intentionally NOT production-role scoped:
    #  - create/list (no production yet / filters itself)
    #  - the public invite-token lookup + accept (token IS the credential)
    WHITELIST = {
        "production.create_production",
        "production.list_productions",
        "production.get_production_invite",
        "production.accept_production_invite",
    }
    # Owner-only spine routes still use the inline _user_owns_production guard,
    # not the decorator — track them explicitly so this test documents them.
    INLINE_OWNER_GUARD = {
        "production.get_production",
        "production.delete_production",
        "production.add_script_to_production",
        "production.remove_script_from_production",
    }

    SCOPED_ARGS = {"production_id", "crew_id", "member_id", "invite_id"}

    for rule in app.url_map.iter_rules():
        if not rule.endpoint.startswith("production."):
            continue
        if rule.endpoint in WHITELIST or rule.endpoint in INLINE_OWNER_GUARD:
            continue
        if not (set(rule.arguments) & SCOPED_ARGS):
            continue
        view = app.view_functions[rule.endpoint]
        assert hasattr(view, "_authz_min_role") or hasattr(view, "_authz_capability"), \
            f"{rule.endpoint} is production-scoped but has no require_production_role marker"
