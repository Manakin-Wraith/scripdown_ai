import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
import services.casting_group_service as g
import routes.casting_routes as cr
import middleware.authorization as authz


# --------------------------------------------------------------------------- #
# Stateful fake Supabase client for the service-layer tests                    #
# --------------------------------------------------------------------------- #
class FakeTable:
    def __init__(self, store, name):
        self.store, self.name = store, name
        self._filters, self._payload, self._op = [], None, None

    def select(self, *a, **k): self._op = "select"; return self
    def insert(self, payload): self._op, self._payload = "insert", payload; return self
    def update(self, payload): self._op, self._payload = "update", payload; return self
    def delete(self): self._op = "delete"; return self
    def eq(self, col, val): self._filters.append((col, val)); return self
    def in_(self, col, vals): self._filters.append((col, set(vals))); return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self

    def _match(self, row):
        for c, v in self._filters:
            if isinstance(v, set):
                if row.get(c) not in v:
                    return False
            elif row.get(c) != v:
                return False
        return True

    def execute(self):
        rows = self.store.setdefault(self.name, [])
        if self._op == "select":
            return type("R", (), {"data": [r for r in rows if self._match(r)]})
        if self._op == "insert":
            payload = self._payload if isinstance(self._payload, list) else [self._payload]
            for p in payload:
                p.setdefault("id", f"{self.name}-{len(rows) + 1}")
                rows.append(p)
            return type("R", (), {"data": payload})
        if self._op == "update":
            hit = [r for r in rows if self._match(r)]
            for r in hit:
                r.update(self._payload)
            return type("R", (), {"data": hit})
        if self._op == "delete":
            hit = [r for r in rows if self._match(r)]
            self.store[self.name] = [r for r in rows if not self._match(r)]
            return type("R", (), {"data": hit})


class FakeClient:
    def __init__(self, store): self.store = store
    def table(self, name): return FakeTable(self.store, name)


@pytest.fixture
def mock_client(monkeypatch):
    store = {
        "scripts": [{"id": "s1", "user_id": "u1"}],
        "scenes": [
            {"id": "sc1", "script_id": "s1"},
            {"id": "sc2", "script_id": "s1"},
            {"id": "sc3", "script_id": "s1"},
            {"id": "other1", "script_id": "s2"},
        ],
        "casting_groups": [],
        "casting_group_scenes": [],
    }
    monkeypatch.setattr(g, "_client", lambda: FakeClient(store))
    return store


@pytest.fixture
def seed_script():
    return {"id": "s1"}


@pytest.fixture
def seed_user():
    return {"id": "u1"}


@pytest.fixture
def seed_scenes(mock_client):
    return [r for r in mock_client["scenes"] if r["script_id"] == "s1"]


@pytest.fixture
def other_script_scene(mock_client):
    return next(r for r in mock_client["scenes"] if r["script_id"] == "s2")


@pytest.fixture
def seed_group(mock_client, seed_script, seed_user):
    return g.create_group(seed_script["id"], {"label": "Crowd", "headcount": 10},
                          seed_user["id"])


class TestGroupService:
    def test_create_and_list(self, mock_client, seed_script, seed_user):
        row = g.create_group(seed_script["id"],
                             {"label": "Restaurant patrons", "headcount": 12},
                             seed_user["id"])
        assert row["label"] == "Restaurant patrons"
        assert row["headcount"] == 12
        assert row["scene_ids"] == []
        assert [r["id"] for r in g.list_groups(seed_script["id"])] == [row["id"]]

    def test_create_requires_label(self, mock_client, seed_script, seed_user):
        with pytest.raises(ValueError):
            g.create_group(seed_script["id"], {"headcount": 5}, seed_user["id"])

    def test_update_rejects_zero_headcount(self, mock_client, seed_group):
        with pytest.raises(ValueError):
            g.update_group(seed_group["id"], {"headcount": 0})

    def test_update_rejects_bad_status(self, mock_client, seed_group):
        with pytest.raises(ValueError):
            g.update_group(seed_group["id"], {"status": "pencilled"})

    def test_update_missing_group_raises(self, mock_client):
        with pytest.raises(g.GroupNotFound):
            g.update_group("nope", {"status": "booked"})

    def test_set_group_scenes_replace_all(self, mock_client, seed_group, seed_scenes):
        a, b, c = [s["id"] for s in seed_scenes[:3]]
        g.set_group_scenes(seed_group["id"], [a, b])
        assert set(g.list_groups(seed_group["script_id"])[0]["scene_ids"]) == {a, b}
        g.set_group_scenes(seed_group["id"], [b, c])
        assert set(g.list_groups(seed_group["script_id"])[0]["scene_ids"]) == {b, c}

    def test_set_group_scenes_rejects_foreign_scene(self, mock_client, seed_group, other_script_scene):
        with pytest.raises(ValueError):
            g.set_group_scenes(seed_group["id"], [other_script_scene["id"]])

    def test_delete_group(self, mock_client, seed_group):
        g.delete_group(seed_group["id"])
        assert g.list_groups(seed_group["script_id"]) == []


# --------------------------------------------------------------------------- #
# Route-layer tests                                                            #
# --------------------------------------------------------------------------- #
def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture(autouse=True)
def _bypass_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(cr, "get_user_id", lambda: "u1")


def _as_role(monkeypatch, role):
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: role)
    monkeypatch.setattr(authz, "_lookup_script_id", lambda *a, **k: "s1")


class TestGroupRoutes:
    def test_list_requires_viewer(self, monkeypatch):
        monkeypatch.setattr("middleware.auth.DEV_MODE", False)
        assert _client().get("/api/scripts/s1/casting-groups").status_code == 401

    def test_list_forbidden_for_non_member(self, monkeypatch):
        _as_role(monkeypatch, None)
        assert _client().get("/api/scripts/s1/casting-groups").status_code == 403

    def test_list_ok_for_viewer(self, monkeypatch):
        _as_role(monkeypatch, "viewer")
        monkeypatch.setattr(cr.group_service, "list_groups", lambda sid: [])
        r = _client().get("/api/scripts/s1/casting-groups")
        assert r.status_code == 200
        assert r.get_json() == {"groups": []}

    def test_create_requires_admin(self, monkeypatch):
        _as_role(monkeypatch, "viewer")
        r = _client().post("/api/scripts/s1/casting-groups", json={"label": "Crowd"})
        assert r.status_code == 403

    def test_create_ok_for_admin(self, monkeypatch):
        _as_role(monkeypatch, "admin")
        monkeypatch.setattr(cr.group_service, "create_group",
                            lambda sid, data, uid: {"id": "g1", "script_id": sid,
                                                    "label": data["label"], "scene_ids": []})
        r = _client().post("/api/scripts/s1/casting-groups", json={"label": "Crowd"})
        assert r.status_code == 201
        assert r.get_json()["group"]["id"] == "g1"

    def test_create_bad_payload_returns_400(self, monkeypatch):
        _as_role(monkeypatch, "admin")
        def _boom(sid, data, uid): raise ValueError("label is required")
        monkeypatch.setattr(cr.group_service, "create_group", _boom)
        r = _client().post("/api/scripts/s1/casting-groups", json={})
        assert r.status_code == 400

    def test_patch_ok_for_admin(self, monkeypatch):
        _as_role(monkeypatch, "admin")
        monkeypatch.setattr(cr.group_service, "update_group",
                            lambda gid, fields: {"id": gid, "status": fields.get("status")})
        r = _client().patch("/api/casting-groups/g1", json={"status": "booked"})
        assert r.status_code == 200
        assert r.get_json()["group"]["status"] == "booked"

    def test_patch_missing_returns_404(self, monkeypatch):
        _as_role(monkeypatch, "admin")
        def _boom(gid, fields): raise cr.group_service.GroupNotFound(gid)
        monkeypatch.setattr(cr.group_service, "update_group", _boom)
        r = _client().patch("/api/casting-groups/g1", json={"status": "booked"})
        assert r.status_code == 404

    def test_set_scenes_ok(self, monkeypatch):
        _as_role(monkeypatch, "admin")
        monkeypatch.setattr(cr.group_service, "set_group_scenes",
                            lambda gid, ids: ids)
        r = _client().put("/api/casting-groups/g1/scenes", json={"scene_ids": ["sc1"]})
        assert r.status_code == 200
        assert r.get_json()["scene_ids"] == ["sc1"]

    def test_set_scenes_foreign_returns_400(self, monkeypatch):
        _as_role(monkeypatch, "admin")
        def _boom(gid, ids): raise ValueError("scenes not in this script: ['x']")
        monkeypatch.setattr(cr.group_service, "set_group_scenes", _boom)
        r = _client().put("/api/casting-groups/g1/scenes", json={"scene_ids": ["x"]})
        assert r.status_code == 400

    def test_delete_ok_for_admin(self, monkeypatch):
        _as_role(monkeypatch, "admin")
        monkeypatch.setattr(cr.group_service, "delete_group", lambda gid: {"id": gid})
        r = _client().delete("/api/casting-groups/g1")
        assert r.status_code == 200
        assert r.get_json()["success"] is True
