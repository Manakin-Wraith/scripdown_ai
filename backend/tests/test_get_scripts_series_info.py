"""GET /api/scripts: series/season join enrichment (season_id -> seasons -> series)."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.supabase_routes as sr


class FakeQuery:
    """Minimal chainable supabase-py stand-in supporting select/eq/is_/in_/single/execute."""

    def __init__(self, rows):
        self._filtered = list(rows)
        self._single = False

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._filtered = [r for r in self._filtered if r.get(col) == val]
        return self

    def is_(self, col, _val):
        # Only ever called as .is_('user_id', 'null') in this codebase.
        self._filtered = [r for r in self._filtered if r.get(col) is None]
        return self

    def in_(self, col, values):
        values = set(values)
        self._filtered = [r for r in self._filtered if r.get(col) in values]
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        if self._single:
            return SimpleNamespace(data=self._filtered[0] if self._filtered else None)
        return SimpleNamespace(data=self._filtered)


class FakeSupabase:
    def __init__(self, store):
        self.store = store

    def table(self, name):
        return FakeQuery(self.store.get(name, []))


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def _store(scripts=None, seasons=None, series=None):
    return {
        "scripts": scripts or [],
        "script_members": [],
        "seasons": seasons or [],
        "series": series or [],
        "scenes": [],
    }


def test_get_scripts_attaches_series_and_season_info(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    store = _store(
        scripts=[
            {
                "id": "ep1", "user_id": "u1", "title": "Pilot",
                "created_at": "2026-07-20T00:00:00Z",
                "season_id": "sea1", "episode_number": 1,
            },
        ],
        seasons=[{"id": "sea1", "series_id": "ser1", "season_number": 1, "title": None}],
        series=[{"id": "ser1", "title": "Die Testament"}],
    )
    monkeypatch.setattr(sr, "supabase", FakeSupabase(store))

    resp = _client().get("/api/scripts")

    assert resp.status_code == 200
    script = resp.get_json()["scripts"][0]
    assert script["series_id"] == "ser1"
    assert script["series_title"] == "Die Testament"
    assert script["season_number"] == 1
    assert script["season_title"] is None


def test_get_scripts_unassigned_script_has_null_series_fields(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    store = _store(
        scripts=[
            {
                "id": "s1", "user_id": "u1", "title": "Standalone",
                "created_at": "2026-07-20T00:00:00Z",
                "season_id": None, "episode_number": None,
            },
        ],
    )
    monkeypatch.setattr(sr, "supabase", FakeSupabase(store))

    resp = _client().get("/api/scripts")

    assert resp.status_code == 200
    script = resp.get_json()["scripts"][0]
    assert script["series_id"] is None
    assert script["series_title"] is None
    assert script["season_number"] is None
    assert script["season_title"] is None


def test_get_scripts_season_with_titled_season_and_multiple_episodes(monkeypatch):
    """Two episodes in the same titled season both resolve the same series/season names."""
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    store = _store(
        scripts=[
            {
                "id": "ep1", "user_id": "u1", "title": "Ep 1",
                "created_at": "2026-07-20T00:00:00Z",
                "season_id": "sea1", "episode_number": 1,
            },
            {
                "id": "ep2", "user_id": "u1", "title": "Ep 2",
                "created_at": "2026-07-21T00:00:00Z",
                "season_id": "sea1", "episode_number": 2,
            },
        ],
        seasons=[{"id": "sea1", "series_id": "ser1", "season_number": 1, "title": "The Beginning"}],
        series=[{"id": "ser1", "title": "Die Testament"}],
    )
    monkeypatch.setattr(sr, "supabase", FakeSupabase(store))

    resp = _client().get("/api/scripts")

    assert resp.status_code == 200
    scripts_by_id = {s["id"]: s for s in resp.get_json()["scripts"]}
    for script_id in ("ep1", "ep2"):
        assert scripts_by_id[script_id]["series_title"] == "Die Testament"
        assert scripts_by_id[script_id]["season_title"] == "The Beginning"
        assert scripts_by_id[script_id]["season_number"] == 1


def test_get_scripts_orphaned_season_id_degrades_to_null_fields(monkeypatch):
    """A script's season_id pointing at a season absent from the seasons table
    (shouldn't normally happen given ON DELETE SET NULL, but is a documented
    error-handling path) must degrade to null fields, not crash or leak a
    partial join."""
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    store = _store(
        scripts=[
            {
                "id": "ep1", "user_id": "u1", "title": "Orphaned Episode",
                "created_at": "2026-07-20T00:00:00Z",
                "season_id": "sea-missing", "episode_number": 1,
            },
        ],
        seasons=[],
        series=[],
    )
    monkeypatch.setattr(sr, "supabase", FakeSupabase(store))

    resp = _client().get("/api/scripts")

    assert resp.status_code == 200
    script = resp.get_json()["scripts"][0]
    assert script["series_id"] is None
    assert script["series_title"] is None
    assert script["season_number"] is None
    assert script["season_title"] is None
