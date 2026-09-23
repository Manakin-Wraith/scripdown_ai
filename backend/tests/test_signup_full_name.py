"""The signup name must reach profiles.full_name even when set-plan never runs.

Signup stores full_name in Supabase user_metadata (it rides in the JWT), so the
auth middleware's profile safety net and set-plan can both recover it — no
dependence on the signup browser's localStorage.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import middleware.auth as auth_mw
import routes.auth_routes as ar


class _FakeQuery:
    def __init__(self, db, table):
        self.db, self.table, self.op, self.payload, self.filters = db, table, 'select', None, {}

    def select(self, *_a, **_k):
        self.op = 'select'
        return self

    def insert(self, payload):
        self.op, self.payload = 'insert', payload
        return self

    def update(self, payload):
        self.op, self.payload = 'update', payload
        return self

    def eq(self, col, val):
        self.filters[col] = val
        return self

    def is_(self, col, val):
        self.filters[col] = None if val == 'null' else val
        return self

    def execute(self):
        rows = self.db.setdefault(self.table, [])
        match = [r for r in rows if all(r.get(k) == v for k, v in self.filters.items())]
        if self.op == 'insert':
            rows.append(dict(self.payload))
            return type('R', (), {'data': [self.payload]})()
        if self.op == 'update':
            for r in match:
                r.update(self.payload)
            return type('R', (), {'data': match})()
        return type('R', (), {'data': match})()


class _FakeAdmin:
    def __init__(self, db):
        self.db = db

    def table(self, name):
        return _FakeQuery(self.db, name)


def _patch_admin(monkeypatch, db):
    import db.supabase_client as sc
    monkeypatch.setattr(sc, "get_supabase_admin", lambda: _FakeAdmin(db))


def test_new_profile_takes_full_name_from_metadata(monkeypatch):
    db = {'profiles': []}
    _patch_admin(monkeypatch, db)
    auth_mw._ensure_profile_exists({'sub': 'u1', 'email': 'a@x.com',
                                    'user_metadata': {'full_name': ' Kaylee Smith '}})
    assert db['profiles'] == [{'id': 'u1', 'email': 'a@x.com', 'full_name': 'Kaylee Smith'}]


def test_new_profile_without_metadata_name_has_no_full_name(monkeypatch):
    db = {'profiles': []}
    _patch_admin(monkeypatch, db)
    auth_mw._ensure_profile_exists({'sub': 'u1', 'email': 'a@x.com'})
    assert db['profiles'] == [{'id': 'u1', 'email': 'a@x.com'}]


def test_existing_nameless_profile_is_filled_from_metadata(monkeypatch):
    db = {'profiles': [{'id': 'u1', 'email': 'a@x.com', 'full_name': None}]}
    _patch_admin(monkeypatch, db)
    auth_mw._ensure_profile_exists({'sub': 'u1', 'user_metadata': {'full_name': 'Kaylee'}})
    assert db['profiles'][0]['full_name'] == 'Kaylee'


def test_existing_name_is_never_overwritten(monkeypatch):
    # The profile page is where a user renames themselves; metadata from
    # signup must not clobber that on every request.
    db = {'profiles': [{'id': 'u1', 'full_name': 'Renamed Later'}]}
    _patch_admin(monkeypatch, db)
    auth_mw._ensure_profile_exists({'sub': 'u1', 'user_metadata': {'full_name': 'Signup Name'}})
    assert db['profiles'][0]['full_name'] == 'Renamed Later'


def test_set_plan_falls_back_to_metadata_name(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(ar, "get_user_id", lambda: 'u1')
    monkeypatch.setattr(ar, "get_current_user", lambda: {
        'id': 'u1', 'email': 'a@x.com', 'user_metadata': {'full_name': 'Meta Name'}})
    written = {}
    monkeypatch.setattr(ar, "_upsert_profile", lambda uid, data: written.update(data))
    from app import app
    app.config["TESTING"] = True
    app.test_client().post("/api/auth/set-plan", json={'plan': 'tier_1'})
    assert written['full_name'] == 'Meta Name'
