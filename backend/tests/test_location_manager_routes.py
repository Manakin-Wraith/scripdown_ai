"""Location manager endpoints require auth + owner/member access."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.supabase_routes as sr


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def test_rename_parent_requires_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().post("/api/scripts/s1/locations/rename-parent",
                          json={"from_canonical": "VILLA", "to_name": "SMITH RESIDENCE"})
    assert resp.status_code == 401


def test_rename_parent_forbidden_for_non_member(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u2")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: False)
    resp = _client().post("/api/scripts/s1/locations/rename-parent",
                          json={"from_canonical": "VILLA", "to_name": "SMITH RESIDENCE"})
    assert resp.status_code == 403


def test_rename_parent_ok_calls_helper(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    monkeypatch.setattr(sr, "_rename_parent", lambda script_id, frm, to, uid: 4)
    resp = _client().post("/api/scripts/s1/locations/rename-parent",
                          json={"from_canonical": "VILLA", "to_name": "SMITH RESIDENCE"})
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "scenes_updated": 4}


def test_rename_parent_validates_body(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    resp = _client().post("/api/scripts/s1/locations/rename-parent", json={"to_name": "X"})
    assert resp.status_code == 400


def test_rename_sub_forbidden_for_non_member(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u2")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: False)
    resp = _client().post("/api/scripts/s1/locations/rename-sub",
                          json={"parent_canonical": "VILLA", "from_sub": "POOL", "to_sub": "SWIMMING POOL"})
    assert resp.status_code == 403


def test_rename_sub_ok_calls_helper(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    monkeypatch.setattr(sr, "_rename_sub", lambda script_id, parent, frm, to, uid: 2)
    resp = _client().post("/api/scripts/s1/locations/rename-sub",
                          json={"parent_canonical": "VILLA", "from_sub": "POOL", "to_sub": "SWIMMING POOL"})
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "scenes_updated": 2}


def test_rename_sub_validates_body(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    resp = _client().post("/api/scripts/s1/locations/rename-sub",
                          json={"parent_canonical": "VILLA", "from_sub": "POOL"})
    assert resp.status_code == 400


def test_reassign_scene_forbidden(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u2")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: False)
    resp = _client().post("/api/scripts/s1/locations/reassign-scene",
                          json={"scene_id": "sc1", "to_parent_name": "HOTEL"})
    assert resp.status_code == 403


def test_reassign_scene_ok(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    monkeypatch.setattr(sr, "_reassign_scene", lambda script_id, scid, to: 1)
    resp = _client().post("/api/scripts/s1/locations/reassign-scene",
                          json={"scene_id": "sc1", "to_parent_name": "HOTEL"})
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "scenes_updated": 1}


def test_merge_parents_ok_sums_sources(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    calls = []
    monkeypatch.setattr(sr, "_rename_parent",
                        lambda script_id, frm, to, uid: calls.append((frm, to)) or 3)
    resp = _client().post("/api/scripts/s1/locations/merge-parents",
                          json={"canonical_name": "VILLA", "source_canonicals": ["THE VILLA", "VILLA HOUSE"]})
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "scenes_updated": 6}
    assert calls == [("THE VILLA", "VILLA"), ("VILLA HOUSE", "VILLA")]


def test_merge_parents_validates_body(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    resp = _client().post("/api/scripts/s1/locations/merge-parents",
                          json={"canonical_name": "VILLA", "source_canonicals": []})
    assert resp.status_code == 400


def test_rename_parent_reparents_sub_aliases(monkeypatch):
    # _rename_parent must re-point existing sub_location_aliases from the old
    # parent key to the new one, so sticky sub renames survive a parent rename.
    calls = []

    class _Q:
        def __init__(self, table):
            self.table = table
            self._eq = {}
            self._update = None
        def select(self, *a, **k):
            return self
        def update(self, payload):
            self._update = payload
            return self
        def upsert(self, *a, **k):
            return self
        def ilike(self, col, val):
            self._eq[col] = ('ilike', val)
            return self
        def eq(self, col, val):
            self._eq[col] = val
            return self
        def execute(self):
            calls.append((self.table, self._update, dict(self._eq)))
            class _R:
                data = []
            return _R()

    class _FakeSupa:
        def table(self, name):
            return _Q(name)

    monkeypatch.setattr(sr, "supabase", _FakeSupa())
    sr._rename_parent("s1", "VILLA", "SMITH RESIDENCE", "u1")

    assert any(
        t == "sub_location_aliases"
        and u == {"parent_place": "SMITH RESIDENCE"}
        and eqs.get("parent_place") == "VILLA"
        for (t, u, eqs) in calls
    ), f"expected a sub_location_aliases re-point call; got {calls}"


def test_nest_forbidden_for_non_member(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u2")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: False)
    resp = _client().post("/api/scripts/s1/locations/nest",
                          json={"source_canonical": "GARAGE", "parent_name": "VILLA"})
    assert resp.status_code == 403

def test_nest_validates_body(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    resp = _client().post("/api/scripts/s1/locations/nest", json={"parent_name": "VILLA"})
    assert resp.status_code == 400

def test_nest_ok_calls_helper(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "_user_can_access_script", lambda sid, uid: True)
    monkeypatch.setattr(sr, "_nest", lambda script_id, src, parent, uid: 5)
    resp = _client().post("/api/scripts/s1/locations/nest",
                          json={"source_canonical": "GARAGE", "parent_name": "VILLA"})
    assert resp.status_code == 200
    assert resp.get_json() == {"success": True, "scenes_updated": 5}

def test_nest_helper_sets_parent_base_canonical(monkeypatch):
    # _nest must set location_canonical to the parent BASE (VILLA), write
    # hierarchy [VILLA, set], and upsert a location_aliases row with set_name.
    calls = []
    class _Q:
        def __init__(self, table):
            self.table = table; self._eq = {}; self._update = None; self._upsert = None
        def select(self, *a, **k): return self
        def update(self, payload): self._update = payload; return self
        def upsert(self, payload, *a, **k): self._upsert = payload; return self
        def eq(self, col, val): self._eq[col] = val; return self
        def execute(self):
            calls.append((self.table, self._update, self._upsert, dict(self._eq)))
            class _R:
                data = [{"id": "sc1", "int_ext": "INT", "time_of_day": "DAY"}] \
                    if self.table == "scenes" and self._update is None else []
            return _R()
    class _FakeSupa:
        def table(self, name): return _Q(name)
    monkeypatch.setattr(sr, "supabase", _FakeSupa())
    n = sr._nest("s1", "GARAGE / BACKROOM", "VILLA", "u1")
    assert n == 1
    scene_updates = [u for (t, u, _up, _eq) in calls if t == "scenes" and u is not None]
    assert scene_updates and scene_updates[0]["location_canonical"] == "VILLA"
    assert scene_updates[0]["location_hierarchy"] == ["VILLA", "GARAGE / BACKROOM"]
    upserts = [up for (t, _u, up, _eq) in calls if t == "location_aliases" and up is not None]
    assert upserts and upserts[0]["set_name"] == "GARAGE / BACKROOM" \
        and upserts[0]["canonical_place"] == "VILLA" and upserts[0]["alias_place"] == "GARAGE / BACKROOM"
