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
from postgrest.exceptions import APIError


class MockTable:
    """Chainable supabase-py stand-in supporting select/insert/eq/order/single/limit."""

    def __init__(self, name, store):
        self.name = name
        self.store = store
        self._filters = {}
        self._op = None
        self._payload = None
        self._single = False
        self._order_col = None
        self._limit = None

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

    def limit(self, n):
        self._limit = n
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
            if self._limit is not None:
                matches = matches[:self._limit]
            if self._single:
                # Match real supabase-py behavior: .single() with zero matches
                # makes PostgREST respond 406, which postgrest-py surfaces as
                # an APIError with code 'PGRST116' -- not a graceful data=None.
                if not matches:
                    raise APIError({
                        "message": "JSON object requested, multiple (or no) rows returned",
                        "code": "PGRST116",
                        "hint": None,
                        "details": None,
                    })
                return SimpleNamespace(data=matches[0])
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


def test_list_seasons_visible_to_non_owner_with_episode_access(monkeypatch):
    """A non-owner who has access to at least one episode script inside one
    of the series' seasons can still see the season list -- the shared-link
    visibility path, not the owner path."""
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["series"] = [{"id": "ser1", "owner_id": "someone-else", "title": "Not Mine"}]
    store["seasons"] = [
        {"id": "sea1", "series_id": "ser1", "season_number": 1, "title": None},
    ]
    store["scripts"] = [
        {"id": "ep1", "user_id": DEV_USER_ID, "season_id": "sea1", "episode_number": 1, "title": "Ep 1"},
    ]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))
    monkeypatch.setattr("middleware.authorization.get_supabase_client", lambda: MockSupabase(store))

    resp = _client().get("/api/series/ser1/seasons")

    assert resp.status_code == 200
    numbers = [s["season_number"] for s in resp.get_json()["seasons"]]
    assert numbers == [1]


def test_list_seasons_forbidden_for_non_owner_without_episode_access(monkeypatch):
    """A non-owner with no accessible script in any season of the series
    must be blocked -- season structure isn't discoverable by strangers."""
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["series"] = [{"id": "ser1", "owner_id": "someone-else", "title": "Not Mine"}]
    store["seasons"] = [
        {"id": "sea1", "series_id": "ser1", "season_number": 1, "title": None},
    ]
    store["scripts"] = [
        {"id": "ep1", "user_id": "someone-else", "season_id": "sea1", "episode_number": 1, "title": "Ep 1"},
    ]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))
    monkeypatch.setattr("middleware.authorization.get_supabase_client", lambda: MockSupabase(store))

    resp = _client().get("/api/series/ser1/seasons")

    assert resp.status_code == 403
    body = resp.get_json()
    assert "error" in body


def test_create_season_nonexistent_series_returns_clean_error(monkeypatch):
    """Verify that requesting a nonexistent series doesn't crash unhandled."""
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))

    resp = _client().post("/api/series/nonexistent/seasons", json={"season_number": 2})

    # create_season is ownership-gated via _user_owns_series, which folds
    # "series doesn't exist" and "series exists but caller doesn't own it"
    # into the same 403 -- by design (see series_routes.py module docstring),
    # not a bug. What matters here is that the now-fixed .single() no longer
    # leaks a raw 500 for a missing series; it resolves cleanly to 403.
    assert resp.status_code == 403
    body = resp.get_json()
    assert "error" in body


def test_list_seasons_nonexistent_series_returns_clean_error(monkeypatch):
    """Verify that listing seasons for nonexistent series doesn't crash unhandled."""
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))

    resp = _client().get("/api/series/nonexistent/seasons")

    # list_seasons explicitly checks series existence via _get_series and
    # returns a clean 404 -- must not leak a raw 500 from the underlying
    # .single() APIError.
    assert resp.status_code == 404
    body = resp.get_json()
    assert "error" in body
    assert "not found" in body["error"].lower()


def test_list_episodes_filters_to_accessible_scripts(monkeypatch):
    """
    The core access-control guarantee of this feature: a season's episode
    list must never leak a script the caller can't otherwise see, even
    though it's returned by season_id rather than the usual
    /api/scripts/<script_id> path.
    """
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["scripts"] = [
        {"id": "ep1", "user_id": DEV_USER_ID, "season_id": "sea1", "episode_number": 1, "title": "Ep 1"},
        {"id": "ep2", "user_id": "someone-else", "season_id": "sea1", "episode_number": 2, "title": "Ep 2"},
    ]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))
    monkeypatch.setattr("middleware.authorization.get_supabase_client", lambda: MockSupabase(store))

    resp = _client().get("/api/seasons/sea1/episodes")

    assert resp.status_code == 200
    episodes = resp.get_json()["episodes"]
    assert [e["id"] for e in episodes] == ["ep1"]  # ep2 filtered out, not owner or member


def test_list_episodes_orders_by_episode_number(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["scripts"] = [
        {"id": "ep2", "user_id": DEV_USER_ID, "season_id": "sea1", "episode_number": 2, "title": "Ep 2"},
        {"id": "ep1", "user_id": DEV_USER_ID, "season_id": "sea1", "episode_number": 1, "title": "Ep 1"},
    ]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))
    monkeypatch.setattr("middleware.authorization.get_supabase_client", lambda: MockSupabase(store))

    resp = _client().get("/api/seasons/sea1/episodes")

    numbers = [e["episode_number"] for e in resp.get_json()["episodes"]]
    assert numbers == [1, 2]


def test_update_script_season_requires_series_ownership(monkeypatch):
    """A member on the script cannot move it into a season on a series they
    don't own -- prevents sneaking a script into someone else's series."""
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["scripts"] = [{"id": "s1", "user_id": DEV_USER_ID, "season_id": None, "episode_number": None}]
    store["series"] = [{"id": "ser1", "owner_id": "someone-else", "title": "Not Mine"}]
    store["seasons"] = [{"id": "sea1", "series_id": "ser1", "season_number": 1}]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))
    monkeypatch.setattr("middleware.authorization.get_supabase_client", lambda: MockSupabase(store))

    resp = _client().patch("/api/scripts/s1/season", json={"season_id": "sea1", "episode_number": 3})

    assert resp.status_code == 403
    assert store["scripts"][0]["season_id"] is None


def test_update_script_season_assigns_when_owned(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["scripts"] = [{"id": "s1", "user_id": DEV_USER_ID, "season_id": None, "episode_number": None}]
    store["series"] = [{"id": "ser1", "owner_id": DEV_USER_ID, "title": "Mine"}]
    store["seasons"] = [{"id": "sea1", "series_id": "ser1", "season_number": 1}]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))
    monkeypatch.setattr("middleware.authorization.get_supabase_client", lambda: MockSupabase(store))

    resp = _client().patch("/api/scripts/s1/season", json={"season_id": "sea1", "episode_number": 3})

    assert resp.status_code == 200
    assert store["scripts"][0]["season_id"] == "sea1"
    assert store["scripts"][0]["episode_number"] == 3


def test_update_script_season_clears_assignment(monkeypatch):
    """season_id: null removes a script from its season -- the reassignment
    surface's 'None' state."""
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["scripts"] = [{"id": "s1", "user_id": DEV_USER_ID, "season_id": "sea1", "episode_number": 3}]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))
    monkeypatch.setattr("middleware.authorization.get_supabase_client", lambda: MockSupabase(store))

    resp = _client().patch("/api/scripts/s1/season", json={"season_id": None})

    assert resp.status_code == 200
    assert store["scripts"][0]["season_id"] is None
    assert store["scripts"][0]["episode_number"] is None


def test_update_script_season_nonexistent_season_returns_404(monkeypatch):
    """Verify that trying to assign a script to a nonexistent season returns
    a clean 404 with error message, not a crash or leaked exception."""
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["scripts"] = [{"id": "s1", "user_id": DEV_USER_ID, "season_id": None, "episode_number": None}]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))
    monkeypatch.setattr("middleware.authorization.get_supabase_client", lambda: MockSupabase(store))

    resp = _client().patch("/api/scripts/s1/season", json={"season_id": "nonexistent", "episode_number": 1})

    assert resp.status_code == 404
    body = resp.get_json()
    assert "error" in body
    assert "not found" in body["error"].lower()
    # Verify script wasn't updated
    assert store["scripts"][0]["season_id"] is None


def test_combined_cast_groups_exact_name_case_insensitive(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["scripts"] = [
        {"id": "ep1", "user_id": DEV_USER_ID, "season_id": "sea1", "episode_number": 1, "title": "Ep 1"},
        {"id": "ep2", "user_id": DEV_USER_ID, "season_id": "sea1", "episode_number": 2, "title": "Ep 2"},
    ]
    store["scenes"] = [
        {"id": "sc1", "script_id": "ep1", "characters": ["JOHN", "MARY"]},
        {"id": "sc2", "script_id": "ep2", "characters": ["John", "SAM"]},  # case-only variant of JOHN
    ]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))
    monkeypatch.setattr("middleware.authorization.get_supabase_client", lambda: MockSupabase(store))

    resp = _client().get("/api/seasons/sea1/cast")

    assert resp.status_code == 200
    cast = {row["name"]: row["episodes"] for row in resp.get_json()["cast"]}
    assert set(cast.keys()) == {"JOHN", "MARY", "SAM"}
    assert sorted(cast["JOHN"]) == ["Ep 1", "Ep 2"]  # grouped across both episodes
    assert cast["MARY"] == ["Ep 1"]
    assert cast["SAM"] == ["Ep 2"]


def test_combined_cast_only_includes_accessible_episodes(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    store = _base_store()
    store["scripts"] = [
        {"id": "ep1", "user_id": DEV_USER_ID, "season_id": "sea1", "episode_number": 1, "title": "Ep 1"},
        {"id": "ep2", "user_id": "someone-else", "season_id": "sea1", "episode_number": 2, "title": "Ep 2"},
    ]
    store["scenes"] = [
        {"id": "sc1", "script_id": "ep1", "characters": ["JOHN"]},
        {"id": "sc2", "script_id": "ep2", "characters": ["SECRET"]},
    ]
    monkeypatch.setattr(sr, "get_supabase_admin", lambda: MockSupabase(store))
    monkeypatch.setattr("middleware.authorization.get_supabase_client", lambda: MockSupabase(store))

    resp = _client().get("/api/seasons/sea1/cast")

    names = {row["name"] for row in resp.get_json()["cast"]}
    assert names == {"JOHN"}  # SECRET (from the inaccessible ep2) never leaks
