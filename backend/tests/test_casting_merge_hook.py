"""Task 7: the character-merge route must carry `casting` rows from an alias
name to the new canonical name (renaming, or deleting on collision)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.supabase_routes as sr


class Tbl:
    def __init__(self, store, name):
        self.store, self.name, self._f, self._op, self._payload = store, name, [], None, None

    def select(self, *a, **k):
        self._op = "select"; return self

    def update(self, p):
        self._op, self._payload = "update", p; return self

    def delete(self):
        self._op = "delete"; return self

    def insert(self, p):
        self._op, self._payload = "insert", p; return self

    def upsert(self, p, **k):
        self._op, self._payload = "insert", p; return self

    def eq(self, c, v):
        self._f.append((c, v)); return self

    def execute(self):
        rows = self.store.setdefault(self.name, [])
        m = lambda r: all(r.get(c) == v for c, v in self._f)
        if self._op == "select":
            return type("R", (), {"data": [r for r in rows if m(r)]})
        if self._op == "update":
            hit = [r for r in rows if m(r)]
            for r in hit:
                r.update(self._payload)
            return type("R", (), {"data": hit})
        if self._op == "delete":
            self.store[self.name] = [r for r in rows if not m(r)]
            return type("R", (), {"data": []})
        if self._op == "insert":
            rows.append(self._payload)
            return type("R", (), {"data": [self._payload]})


class Client:
    def __init__(self, store):
        self.store = store

    def table(self, name):
        return Tbl(self.store, name)


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def _run_merge(monkeypatch, store, canonical, aliases):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(sr, "get_user_id", lambda: "u1")
    monkeypatch.setattr(sr, "supabase", Client(store))
    resp = _client().post(
        "/api/scripts/s1/characters/merge",
        json={"canonical_name": canonical, "aliases": aliases},
    )
    assert resp.status_code == 200, resp.get_json()
    return resp


def test_merge_renames_casting_row(monkeypatch):
    store = {
        "scenes": [{"id": "sc1", "script_id": "s1", "characters": ["JON"]}],
        "character_aliases": [],
        "casting": [{"id": "c1", "script_id": "s1", "character_name": "JON"}],
    }
    _run_merge(monkeypatch, store, "JOHN", ["JON"])
    assert store["casting"][0]["character_name"] == "JOHN"


def test_merge_collision_deletes_alias_casting_row(monkeypatch):
    store = {
        "scenes": [{"id": "sc1", "script_id": "s1", "characters": ["JON", "JOHN"]}],
        "character_aliases": [],
        "casting": [
            {"id": "c1", "script_id": "s1", "character_name": "JOHN"},
            {"id": "c2", "script_id": "s1", "character_name": "JON"},
        ],
    }
    _run_merge(monkeypatch, store, "JOHN", ["JON"])
    names = sorted(r["character_name"] for r in store["casting"])
    assert names == ["JOHN"]
