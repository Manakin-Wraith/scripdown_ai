"""Production member + invite tests.

MockTable / MockSupabase are the chainable in-memory stand-in shared across
the production suite (copied from test_production_crew_routes.py).
"""
import os, sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.production_member_service as pms
from middleware.auth import DEV_USER_ID


def _ilike_match(cell, pattern):
    c = str(cell or "").lower()
    p = str(pattern).lower()
    if "%" in p:
        return p.strip("%") in c
    return c == p


def _or_match(row, expr):
    for clause in expr.split(","):
        col, op, val = clause.split(".", 2)
        if op == "ilike" and _ilike_match(row.get(col), val):
            return True
    return False


class MockTable:
    def __init__(self, name, store):
        self.name = name
        self.store = store
        self._filters = {}          # col -> value for .eq
        self._is_null = set()       # cols asserted IS NULL via .is_
        self._ilike = []            # (col, pattern) from .ilike
        self._or = None             # raw PostgREST or_ expression
        self._op = None
        self._payload = None
        self._single = False
        self._order = None
        self._limit = None

    def select(self, *_a, **_k):
        self._op = "select"; return self

    def insert(self, data):
        self._op = "insert"; self._payload = data; return self

    def update(self, data):
        self._op = "update"; self._payload = data; return self

    def delete(self):
        self._op = "delete"; return self

    def eq(self, col, val):
        self._filters[col] = val; return self

    def is_(self, col, _val):        # only ever .is_(col, "null") in this codebase
        self._is_null.add(col); return self

    def in_(self, col, values):
        self._filters[col] = ("__in__", set(values)); return self

    def ilike(self, col, pattern):
        self._ilike.append((col, pattern)); return self

    def or_(self, expr):
        self._or = expr; return self

    def order(self, col, desc=False):
        self._order = (col, desc); return self

    def single(self):
        self._single = True; return self

    def limit(self, n):
        self._limit = n; return self

    def _rows(self):
        return self.store.setdefault(self.name, [])

    def _match(self, r):
        for k, v in self._filters.items():
            if isinstance(v, tuple) and v and v[0] == "__in__":
                if r.get(k) not in v[1]:
                    return False
            elif r.get(k) != v:
                return False
        for col in self._is_null:
            if r.get(col) is not None:
                return False
        for col, pattern in self._ilike:
            if not _ilike_match(r.get(col), pattern):
                return False
        if self._or is not None and not _or_match(r, self._or):
            return False
        return True

    def _filtered(self):
        rows = [r for r in self._rows() if self._match(r)]
        if self._order:
            col, desc = self._order
            rows = sorted(rows, key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
        return rows

    def execute(self):
        if self._op == "select":
            rows = self._filtered()
            if self._limit is not None:
                rows = rows[: self._limit]
            if self._single:
                from postgrest.exceptions import APIError
                if not rows:
                    raise APIError({"message": "no rows", "code": "PGRST116",
                                    "hint": None, "details": None})
                return SimpleNamespace(data=rows[0])
            return SimpleNamespace(data=rows)
        if self._op == "insert":
            row = dict(self._payload)
            row.setdefault("id", f"{self.name}-{len(self._rows()) + 1}")
            self._rows().append(row)
            return SimpleNamespace(data=[row])
        if self._op == "update":
            rows = self._filtered()
            for r in rows:
                r.update(self._payload)
            return SimpleNamespace(data=rows)
        if self._op == "delete":
            rows = self._filtered()
            keep = [r for r in self._rows() if r not in rows]
            self.store[self.name] = keep
            return SimpleNamespace(data=rows)
        return SimpleNamespace(data=None)


class MockSupabase:
    def __init__(self, store):
        self.store = store

    def table(self, name):
        return MockTable(name, self.store)


def _patch(monkeypatch, store):
    mock = MockSupabase(store)
    monkeypatch.setattr(pms, "get_supabase_admin", lambda: mock)
    return mock


def test_apply_role_preset_admin():
    assert pms.apply_role_preset("admin", None) == {
        "can_view_sensitive": True, "can_edit_crew": True,
        "can_manage_members": True, "can_edit_production": True}


def test_apply_role_preset_coordinator():
    assert pms.apply_role_preset("coordinator", None) == {
        "can_view_sensitive": False, "can_edit_crew": True,
        "can_manage_members": False, "can_edit_production": False}


def test_apply_role_preset_with_override():
    out = pms.apply_role_preset("coordinator", {"can_view_sensitive": True})
    assert out["can_view_sensitive"] is True and out["can_edit_crew"] is True


def test_rank_ok_owner_can_anything():
    owner = {"role": "owner", "can_manage_members": True, "can_edit_crew": True,
             "can_view_sensitive": True, "can_edit_production": True}
    assert pms.rank_ok(owner, "admin", pms.apply_role_preset("admin", None)) is True


def test_rank_ok_admin_cannot_create_admin():
    admin = {"role": "admin", "can_manage_members": True, "can_edit_crew": True,
             "can_view_sensitive": True, "can_edit_production": True}
    assert pms.rank_ok(admin, "admin", pms.apply_role_preset("admin", None)) is False


def test_rank_ok_admin_can_create_coordinator():
    admin = {"role": "admin", "can_manage_members": True, "can_edit_crew": True,
             "can_view_sensitive": True, "can_edit_production": True}
    assert pms.rank_ok(admin, "coordinator", pms.apply_role_preset("coordinator", None)) is True


def test_rank_ok_actor_cannot_grant_flag_they_lack():
    admin_no_manage = {"role": "admin", "can_manage_members": False, "can_edit_crew": True,
                       "can_view_sensitive": True, "can_edit_production": True}
    flags = pms.apply_role_preset("coordinator", {"can_manage_members": True})
    assert pms.rank_ok(admin_no_manage, "coordinator", flags) is False


def test_list_members_joins_profile_name(monkeypatch):
    _patch(monkeypatch, {
        "production_members": [{"id": "m1", "production_id": "p1", "user_id": "u1",
                               "role": "coordinator", "can_view_sensitive": False,
                               "can_edit_crew": True, "can_manage_members": False,
                               "can_edit_production": False}],
        "profiles": [{"id": "u1", "full_name": "Lee Producer", "email": "lee@x.com"}],
        "production_invites": [{"id": "i1", "production_id": "p1", "email": "new@x.com",
                              "role": "viewer", "status": "pending", "expires_at": "2099-01-01"}],
    })
    out = pms.list_members_and_invites("p1")
    assert out["members"][0]["name"] == "Lee Producer"
    assert out["members"][0]["email"] == "lee@x.com"
    assert len(out["invites"]) == 1 and out["invites"][0]["email"] == "new@x.com"


import routes.production_routes as pr  # noqa


def _client():
    from flask import Flask
    from routes.production_routes import production_bp
    app = Flask(__name__); app.config["TESTING"] = True
    app.register_blueprint(production_bp)
    return app.test_client()


def _rt_patch(monkeypatch, store):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    mock = MockSupabase(store)
    monkeypatch.setattr(pms, "get_supabase_admin", lambda: mock)
    monkeypatch.setattr("middleware.production_authz.get_supabase_admin", lambda: mock)
    monkeypatch.setattr("middleware.production_authz.get_user_id", lambda: DEV_USER_ID)
    monkeypatch.setattr("services.production_service.get_supabase_admin", lambda: mock)
    # owner is Tier-2 active with spare seats unless a test overrides
    monkeypatch.setattr(pms, "get_entitlement", lambda uid: {
        "can_use_teams": True, "seats_used": 0, "seats_paid": 10})
    monkeypatch.setattr("services.email_service.is_configured", lambda: False)


def _owned_store(**ov):
    base = {"productions": [{"id": "p1", "owner_id": DEV_USER_ID, "title": "Farm Feature"}],
            "production_members": [], "production_invites": [],
            "profiles": [{"id": DEV_USER_ID, "full_name": "Owner", "email": "dev@example.com"}],
            "notifications": []}
    base.update(ov)
    return base


def test_get_members_requires_membership(monkeypatch):
    _rt_patch(monkeypatch, {"productions": [{"id": "p1", "owner_id": "other"}],
                            "production_members": [], "production_invites": [], "profiles": []})
    assert _client().get("/api/productions/p1/members").status_code == 403


def test_get_members_owner_ok(monkeypatch):
    _rt_patch(monkeypatch, _owned_store())
    r = _client().get("/api/productions/p1/members")
    assert r.status_code == 200 and r.get_json() == {"members": [], "invites": []}


def test_add_member_existing_account_is_immediate(monkeypatch):
    store = _owned_store(profiles=[
        {"id": DEV_USER_ID, "full_name": "Owner", "email": "dev@example.com"},
        {"id": "u-lee", "full_name": "Lee", "email": "lee@x.com"}])
    _rt_patch(monkeypatch, store)
    r = _client().post("/api/productions/p1/members",
                       json={"email": "lee@x.com", "role": "coordinator"})
    assert r.status_code == 201
    assert r.get_json()["member"]["role"] == "coordinator"
    assert store["production_members"][0]["user_id"] == "u-lee"
    assert store["production_members"][0]["can_edit_crew"] is True
    assert store["production_invites"] == []


def test_add_member_unknown_email_creates_pending_invite(monkeypatch):
    store = _owned_store()
    _rt_patch(monkeypatch, store)
    r = _client().post("/api/productions/p1/members",
                       json={"email": "stranger@x.com", "role": "viewer"})
    assert r.status_code == 201
    assert r.get_json()["invite"]["email"] == "stranger@x.com"
    assert store["production_invites"][0]["status"] == "pending"
    assert store["production_invites"][0]["token"]


def test_add_member_duplicate_is_409(monkeypatch):
    store = _owned_store(
        profiles=[{"id": DEV_USER_ID, "email": "dev@example.com"},
                  {"id": "u-lee", "email": "lee@x.com"}],
        production_members=[{"id": "m1", "production_id": "p1", "user_id": "u-lee", "role": "viewer"}])
    _rt_patch(monkeypatch, store)
    r = _client().post("/api/productions/p1/members", json={"email": "lee@x.com", "role": "viewer"})
    assert r.status_code == 409


def test_add_member_override_persists(monkeypatch):
    store = _owned_store(profiles=[{"id": DEV_USER_ID, "email": "dev@example.com"},
                                   {"id": "u-lee", "email": "lee@x.com"}])
    _rt_patch(monkeypatch, store)
    _client().post("/api/productions/p1/members",
                   json={"email": "lee@x.com", "role": "coordinator", "can_view_sensitive": True})
    assert store["production_members"][0]["can_view_sensitive"] is True


def test_add_member_owner_not_tier2_is_403(monkeypatch):
    store = _owned_store(profiles=[{"id": DEV_USER_ID, "email": "dev@example.com"},
                                   {"id": "u-lee", "email": "lee@x.com"}])
    _rt_patch(monkeypatch, store)
    monkeypatch.setattr(pms, "get_entitlement", lambda uid: {
        "can_use_teams": False, "seats_used": 0, "seats_paid": 10})
    r = _client().post("/api/productions/p1/members", json={"email": "lee@x.com", "role": "viewer"})
    assert r.status_code == 403 and r.get_json()["code"] == "tier_2_required"


def test_add_member_no_seats_is_402(monkeypatch):
    store = _owned_store(profiles=[{"id": DEV_USER_ID, "email": "dev@example.com"},
                                   {"id": "u-lee", "email": "lee@x.com"}])
    _rt_patch(monkeypatch, store)
    monkeypatch.setattr(pms, "get_entitlement", lambda uid: {
        "can_use_teams": True, "seats_used": 10, "seats_paid": 10})
    r = _client().post("/api/productions/p1/members", json={"email": "lee@x.com", "role": "viewer"})
    assert r.status_code == 402 and r.get_json()["code"] == "no_seats_available"


def test_admin_member_cannot_create_admin(monkeypatch):
    store = {"productions": [{"id": "p1", "owner_id": "other", "title": "T"}],
             "production_members": [{"id": "m1", "production_id": "p1", "user_id": DEV_USER_ID,
                                     "role": "admin", "can_manage_members": True, "can_edit_crew": True,
                                     "can_view_sensitive": True, "can_edit_production": True}],
             "production_invites": [],
             "profiles": [{"id": DEV_USER_ID, "email": "dev@example.com"},
                          {"id": "u-x", "email": "x@x.com"}],
             "notifications": []}
    _rt_patch(monkeypatch, store)
    r = _client().post("/api/productions/p1/members", json={"email": "x@x.com", "role": "admin"})
    assert r.status_code == 403 and r.get_json()["code"] == "rank_denied"


def test_patch_member_role(monkeypatch):
    store = _owned_store(production_members=[
        {"id": "m1", "production_id": "p1", "user_id": "u-lee", "role": "viewer",
         "can_view_sensitive": False, "can_edit_crew": False,
         "can_manage_members": False, "can_edit_production": False}],
        profiles=[{"id": DEV_USER_ID, "email": "dev@example.com"},
                  {"id": "u-lee", "email": "lee@x.com"}])
    _rt_patch(monkeypatch, store)
    r = _client().patch("/api/productions/p1/members/m1",
                        json={"role": "coordinator", "can_edit_crew": True})
    assert r.status_code == 200
    assert store["production_members"][0]["role"] == "coordinator"
    assert store["production_members"][0]["can_edit_crew"] is True


def test_delete_member(monkeypatch):
    store = _owned_store(production_members=[
        {"id": "m1", "production_id": "p1", "user_id": "u-lee", "role": "viewer"}],
        profiles=[{"id": DEV_USER_ID, "email": "dev@example.com"}])
    _rt_patch(monkeypatch, store)
    assert _client().delete("/api/productions/p1/members/m1").status_code == 200
    assert store["production_members"] == []


def test_delete_missing_member_is_noop_200(monkeypatch):
    _rt_patch(monkeypatch, _owned_store())
    assert _client().delete("/api/productions/p1/members/nope").status_code == 200


def test_revoke_invite(monkeypatch):
    store = _owned_store(production_invites=[
        {"id": "i1", "production_id": "p1", "email": "x@x.com", "role": "viewer",
         "status": "pending", "expires_at": "2099-01-01"}])
    _rt_patch(monkeypatch, store)
    assert _client().delete("/api/production-invites/i1").status_code == 200
    assert store["production_invites"][0]["status"] == "revoked"


def test_get_invite_by_token_public(monkeypatch):
    store = _owned_store(production_invites=[
        {"id": "i1", "production_id": "p1", "email": "x@x.com", "role": "coordinator",
         "token": "tok1", "status": "pending", "expires_at": "2099-01-01"}])
    _rt_patch(monkeypatch, store)
    r = _client().get("/api/production-invites/token/tok1")
    assert r.status_code == 200
    assert r.get_json()["role"] == "coordinator"
    assert r.get_json()["production_title"] == "Farm Feature"


def test_accept_invite_email_mismatch(monkeypatch):
    store = _owned_store(production_invites=[
        {"id": "i1", "production_id": "p1", "email": "someone-else@x.com", "role": "viewer",
         "token": "tok1", "status": "pending", "expires_at": "2099-01-01"}])
    _rt_patch(monkeypatch, store)
    # DEV_MODE user email is dev@example.com
    r = _client().post("/api/production-invites/token/tok1/accept")
    assert r.status_code == 403 and r.get_json()["code"] == "email_mismatch"


def test_accept_invite_success(monkeypatch):
    store = _owned_store(production_invites=[
        {"id": "i1", "production_id": "p1", "email": "dev@example.com", "role": "coordinator",
         "can_view_sensitive": False, "can_edit_crew": True, "can_manage_members": False,
         "can_edit_production": False, "token": "tok1", "status": "pending",
         "expires_at": "2099-01-01", "invited_by": "owner"}])
    _rt_patch(monkeypatch, store)
    r = _client().post("/api/production-invites/token/tok1/accept")
    assert r.status_code == 200
    assert r.get_json()["production_id"] == "p1"
    assert store["production_members"][0]["user_id"] == DEV_USER_ID
    assert store["production_members"][0]["role"] == "coordinator"
    assert store["production_members"][0]["can_edit_crew"] is True
    assert store["production_invites"][0]["status"] == "accepted"


def test_accept_invite_already_member(monkeypatch):
    store = _owned_store(
        production_members=[{"id": "m1", "production_id": "p1", "user_id": DEV_USER_ID, "role": "viewer"}],
        production_invites=[{"id": "i1", "production_id": "p1", "email": "dev@example.com",
                            "role": "viewer", "token": "tok1", "status": "pending",
                            "expires_at": "2099-01-01"}])
    _rt_patch(monkeypatch, store)
    r = _client().post("/api/production-invites/token/tok1/accept")
    assert r.status_code == 200 and r.get_json()["already_member"] is True
    assert store["production_invites"][0]["status"] == "accepted"


def test_accept_invite_already_used_is_403(monkeypatch):
    """An ACCEPTED invite is not a live credential: a removed member clicking
    the old link must not silently re-consume a seat."""
    store = _owned_store(production_invites=[
        {"id": "i1", "production_id": "p1", "email": "dev@example.com", "role": "viewer",
         "token": "tok1", "status": "accepted", "expires_at": "2099-01-01"}])
    _rt_patch(monkeypatch, store)
    r = _client().post("/api/production-invites/token/tok1/accept")
    assert r.status_code == 403 and r.get_json()["code"] == "invite_already_used"
    assert store["production_members"] == []


def test_add_member_owner_email_is_400(monkeypatch):
    store = _owned_store()
    _rt_patch(monkeypatch, store)
    r = _client().post("/api/productions/p1/members",
                       json={"email": "dev@example.com", "role": "viewer"})
    assert r.status_code == 400 and r.get_json()["code"] == "cannot_target_owner"
    assert store["production_members"] == []


def test_revoke_does_not_clobber_accepted_invite(monkeypatch):
    store = _owned_store(production_invites=[
        {"id": "i1", "production_id": "p1", "email": "x@x.com", "role": "viewer",
         "status": "accepted", "expires_at": "2099-01-01"}])
    _rt_patch(monkeypatch, store)
    assert _client().delete("/api/production-invites/i1").status_code == 200
    assert store["production_invites"][0]["status"] == "accepted"


import routes.invite_routes as ir  # noqa


def test_auto_accept_applies_pending_production_invites(monkeypatch):
    store = {
        "productions": [{"id": "p1", "owner_id": "owner", "title": "T"}],
        "production_members": [], "notifications": [],
        "production_invites": [{"id": "i1", "production_id": "p1", "email": "dev@example.com",
                               "role": "viewer", "token": "tk", "status": "pending",
                               "expires_at": "2099-01-01",
                               "can_view_sensitive": False, "can_edit_crew": False,
                               "can_manage_members": False, "can_edit_production": False}],
        "script_invites": [], "script_members": [], "profiles": [],
    }
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    mock = MockSupabase(store)
    monkeypatch.setattr(ir, "supabase", mock)
    monkeypatch.setattr(pms, "get_supabase_admin", lambda: mock)
    monkeypatch.setattr("services.production_service.get_supabase_admin", lambda: mock)

    from flask import Flask
    app = Flask(__name__); app.config["TESTING"] = True
    app.register_blueprint(ir.invite_bp)
    r = app.test_client().post("/api/invites/auto-accept")
    assert r.status_code == 200
    assert "p1" in r.get_json().get("productions_accepted", [])
    assert store["production_members"][0]["user_id"] == DEV_USER_ID
