"""Team features are tier 2 only, and seat limits are enforced server-side."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.invite_routes as ir
import middleware.authorization as authz


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_tier1_cannot_create_invite(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr("services.entitlement_service.get_user_id", lambda: 'u1')
    monkeypatch.setattr("services.entitlement_service.get_entitlement",
                        lambda uid: {'can_use_teams': False})
    # @require_script_role('admin') now runs before @require_team_tier;
    # give the caller admin so the request reaches the tier gate.
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: 'admin')
    resp = _client().post("/api/scripts/s1/invites", json={'email': 'a@b.com'})
    assert resp.status_code == 403
    assert resp.get_json()['code'] == 'tier_2_required'


def test_departments_list_requires_auth(monkeypatch):
    # Previously had no decorator at all.
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    assert _client().get("/api/invite/departments").status_code == 401
    assert _client().get("/api/departments").status_code == 401


def test_invite_blocked_when_seats_exhausted(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr("services.entitlement_service.get_user_id", lambda: 'owner')
    monkeypatch.setattr("services.entitlement_service.get_entitlement",
                        lambda uid: {'can_use_teams': True})
    monkeypatch.setattr(ir, "get_entitlement",
                        lambda uid: {'can_use_teams': True, 'seats_paid': 2, 'seats_used': 2})
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: 'owner')
    resp = _client().post("/api/scripts/s1/invites", json={'email': 'a@b.com'})
    assert resp.status_code == 402
    assert resp.get_json()['code'] == 'no_seats_available'


def test_superuser_bypasses_exhausted_seats(monkeypatch):
    """Same exhausted-seats state as above, but is_superuser=True must
    bypass the block instead of returning 402."""
    from types import SimpleNamespace
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr("services.entitlement_service.get_user_id", lambda: 'owner')
    monkeypatch.setattr("services.entitlement_service.get_entitlement",
                        lambda uid: {'can_use_teams': True})
    monkeypatch.setattr(ir, "get_entitlement",
                        lambda uid: {'can_use_teams': True, 'seats_paid': 2,
                                      'seats_used': 2, 'is_superuser': True})
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: 'owner')
    monkeypatch.setattr(ir, "get_departments_list",
                        lambda: [{'code': 'camera', 'name': 'Camera'}])

    class _Q:
        def __init__(self, name): self.name = name
        def select(self, *a, **k): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def execute(self):
            # Allow production_id check to pass through safely
            if self.name == 'scripts':
                return SimpleNamespace(data=[])  # no production_id
            raise AssertionError("stop before DB work — seat gate is what's under test")
    monkeypatch.setattr(ir, "supabase", type("S", (), {"table": lambda self, n: _Q(n)})())

    resp = _client().post("/api/scripts/s1/invites",
                          json={'email': 'a@b.com', 'department_code': 'camera'})
    assert resp.status_code != 402


def test_public_invite_token_lookup_stays_public(monkeypatch):
    # An invitee is not yet a member and may not be a tier 2 user — this must
    # NOT be gated, or nobody can ever accept an invite.
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().get("/api/invites/token/sometoken")
    assert resp.status_code != 401


def test_invite_refused_for_production_script(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr("services.entitlement_service.get_user_id", lambda: 'owner')
    monkeypatch.setattr("services.entitlement_service.get_entitlement",
                        lambda uid: {'can_use_teams': True})
    monkeypatch.setattr(ir, "get_entitlement",
                        lambda uid: {'can_use_teams': True, 'seats_paid': 5, 'seats_used': 0})
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: 'owner')

    class _Q:
        def __init__(self, name): self.name = name
        def select(self, *a, **k): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def execute(self):
            if self.name == 'scripts':
                return SimpleNamespace(data=[{'production_id': 'p1'}])
            raise AssertionError(f"unexpected table {self.name}")
    monkeypatch.setattr(ir, "supabase", type("S", (), {"table": lambda self, n: _Q(n)})())

    resp = _client().post("/api/scripts/s1/invites",
                          json={'email': 'a@b.com', 'department_code': 'camera'})
    assert resp.status_code == 409
    body = resp.get_json()
    assert body['code'] == 'managed_by_production'
    assert body['production_id'] == 'p1'
