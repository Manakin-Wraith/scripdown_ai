"""Regression test: character/location merge must accept a genuine
case-only duplicate (e.g. canonical "JOHN", alias "John") and rewrite the
scene's raw string to the canonical spelling, instead of rejecting it as
"nothing to merge"."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.supabase_routes as sr


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_merge_accepts_case_only_character_alias_and_rewrites_scene(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")

    # scenes.characters literally contains the lowercase-variant "John" —
    # a real duplicate that needs collapsing to "JOHN".
    scenes_data = [{"id": "sc1", "characters": ["John", "MARY"]}]
    updates = []

    class _Q:
        def __init__(self, table):
            self.table = table
            self._eq = {}
        def select(self, *a, **k):
            return self
        def update(self, payload):
            updates.append((self.table, dict(self._eq), payload))
            return self
        def upsert(self, *a, **k):
            return self
        def eq(self, col, val):
            self._eq[col] = val
            return self
        def execute(self):
            class _R:
                data = scenes_data if self.table == "scenes" else []
            return _R()

    class _FakeSupa:
        def table(self, name):
            return _Q(name)

    monkeypatch.setattr(sr, "supabase", _FakeSupa())

    resp = _client().post(
        "/api/scripts/s1/characters/merge",
        json={"canonical_name": "JOHN", "aliases": ["John"]},
    )

    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["scenes_updated"] == 1

    scene_updates = [u for (t, _eq, u) in updates if t == "scenes"]
    assert scene_updates == [{"characters": ["JOHN", "MARY"]}]


def test_merge_locations_accepts_case_only_alias_and_rewrites_scene(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)

    scenes_data = [{"id": "sc1", "setting": "villa"}]
    updates = []

    class _Q:
        def __init__(self, table):
            self.table = table
            self._eq = {}
        def select(self, *a, **k):
            return self
        def update(self, payload):
            updates.append((self.table, dict(self._eq), payload))
            return self
        def upsert(self, *a, **k):
            return self
        def eq(self, col, val):
            self._eq[col] = val
            return self
        def execute(self):
            class _R:
                data = scenes_data if self.table == "scenes" else []
            return _R()

    class _FakeSupa:
        def table(self, name):
            return _Q(name)

    monkeypatch.setattr(sr, "supabase", _FakeSupa())

    resp = _client().post(
        "/api/scripts/s1/locations/merge",
        json={"canonical_place": "VILLA", "aliases": ["villa"]},
    )

    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["scenes_updated"] == 1

    scene_updates = [u for (t, _eq, u) in updates if t == "scenes"]
    assert scene_updates and scene_updates[0]["setting"] == "VILLA"


def test_merge_still_rejects_true_no_op_alias(monkeypatch):
    """An alias identical (verbatim) to the canonical spelling is still a
    real no-op and should still be rejected."""
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")

    class _Q:
        def __init__(self, table):
            self.table = table
        def select(self, *a, **k):
            return self
        def eq(self, *a, **k):
            return self
        def execute(self):
            class _R:
                data = []
            return _R()

    class _FakeSupa:
        def table(self, name):
            return _Q(name)

    monkeypatch.setattr(sr, "supabase", _FakeSupa())

    resp = _client().post(
        "/api/scripts/s1/characters/merge",
        json={"canonical_name": "JOHN", "aliases": ["JOHN"]},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "No valid aliases to merge"
