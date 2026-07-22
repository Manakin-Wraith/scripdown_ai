"""
Series/season CRUD route tests.

Mirrors the MockTable/MockSupabase pattern from test_accept_invite.py --
a minimal chainable supabase-py stand-in supporting select/insert/eq/order/
single, backed by a shared in-memory store so route code and any
get_script_role calls see the same data.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.series_routes as sr
from middleware.auth import DEV_USER_ID


class MockTable:
    """Chainable supabase-py stand-in supporting select/insert/eq/order/single."""

    def __init__(self, name, store):
        self.name = name
        self.store = store
        self._filters = {}
        self._op = None
        self._payload = None
        self._single = False
        self._order_col = None

    def select(self, *_a, **_k):
        self._op = "select"
        return self

    def insert(self, data):
        self._op = "insert"
        self._payload = data
        return self

    def update(self, data):
        self._op = "update"
        self._payload = data
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def order(self, col, desc=False):
        self._order_col = (col, desc)
        return self

    def single(self):
        self._single = True
        return self

    def _rows(self):
        return self.store.setdefault(self.name, [])

    def _filtered(self):
        rows = self._rows()
        matches = [r for r in rows if all(r.get(k) == v for k, v in self._filters.items())]
        if self._order_col:
            col, desc = self._order_col
            matches = sorted(matches, key=lambda r: (r.get(col) is None, r.get(col)), reverse=desc)
        return matches

    def execute(self):
        if self._op == "select":
            matches = self._filtered()
            if self._single:
                return SimpleNamespace(data=matches[0] if matches else None)
            return SimpleNamespace(data=matches)
        if self._op == "insert":
            new_row = dict(self._payload)
            new_row.setdefault("id", f"{self.name}-{len(self._rows()) + 1}")
            self._rows().append(new_row)
            return SimpleNamespace(data=[new_row])
        if self._op == "update":
            matches = self._filtered()
            for row in matches:
                row.update(self._payload)
            return SimpleNamespace(data=matches)
        return SimpleNamespace(data=None)


class MockSupabase:
    def __init__(self, store):
        self.store = store

    def table(self, name):
        return MockTable(name, self.store)


def _client():
    from flask import Flask
    from routes.series_routes import series_bp

    test_app = Flask(__name__)
    test_app.config["TESTING"] = True
    test_app.register_blueprint(series_bp)
    return test_app.test_client()


def _base_store():
    return {"series": [], "seasons": [], "scripts": [], "script_members": []}


def test_create_series_creates_series_and_first_season(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))

    resp = _client().post("/api/series", json={"title": "Crime Drama"})

    assert resp.status_code == 201
    body = resp.get_json()
    assert body["series"]["title"] == "Crime Drama"
    assert body["series"]["owner_id"] == DEV_USER_ID
    assert body["season"]["season_number"] == 1
    assert body["season"]["series_id"] == body["series"]["id"]


def test_create_series_requires_title(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))

    resp = _client().post("/api/series", json={})

    assert resp.status_code == 400


def test_list_series_returns_only_callers_own(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["series"] = [
        {"id": "ser1", "owner_id": DEV_USER_ID, "title": "Mine"},
        {"id": "ser2", "owner_id": "someone-else", "title": "Not Mine"},
    ]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))

    resp = _client().get("/api/series")

    assert resp.status_code == 200
    titles = [s["title"] for s in resp.get_json()["series"]]
    assert titles == ["Mine"]


def test_create_season_requires_series_ownership(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["series"] = [{"id": "ser1", "owner_id": "someone-else", "title": "Not Mine"}]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))

    resp = _client().post("/api/series/ser1/seasons", json={"season_number": 2})

    assert resp.status_code == 403
    assert store["seasons"] == []


def test_list_seasons_for_owned_series(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["series"] = [{"id": "ser1", "owner_id": DEV_USER_ID, "title": "Mine"}]
    store["seasons"] = [
        {"id": "sea2", "series_id": "ser1", "season_number": 2, "title": None},
        {"id": "sea1", "series_id": "ser1", "season_number": 1, "title": None},
    ]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))

    resp = _client().get("/api/series/ser1/seasons")

    assert resp.status_code == 200
    numbers = [s["season_number"] for s in resp.get_json()["seasons"]]
    assert numbers == [1, 2]
