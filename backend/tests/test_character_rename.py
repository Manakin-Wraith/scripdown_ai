"""Character rename: rewrites every place a name is stored, keeps the script's
original name for the "originally ..." note, and handles chained renames/reverts."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest

import middleware.authorization as authz
import routes.casting_routes as cr
import services.character_rename_service as svc


class _Q:
    def __init__(self, db, table):
        self.db, self.table = db, table
        self.op, self.payload, self.filters, self.on_conflict = "select", None, [], None

    def select(self, *a, **k): return self
    def update(self, payload): self.op, self.payload = "update", payload; return self
    def delete(self): self.op = "delete"; return self
    def upsert(self, payload, on_conflict=None):
        self.op, self.payload, self.on_conflict = "upsert", payload, on_conflict
        return self
    def eq(self, col, val): self.filters.append((col, "eq", val)); return self
    @property
    def not_(self): return _Not(self)

    def _match(self, row):
        for col, kind, val in self.filters:
            if kind == "eq" and row.get(col) != val: return False
            if kind == "notnull" and row.get(col) is None: return False
        return True

    def execute(self):
        rows = self.db[self.table]
        hit = [r for r in rows if self._match(r)]
        if self.op == "update":
            for r in hit: r.update(self.payload)
        elif self.op == "delete":
            self.db[self.table] = [r for r in rows if r not in hit]
        elif self.op == "upsert":
            keys = self.on_conflict.split(",")
            for r in rows:
                if all(r.get(k) == self.payload.get(k) for k in keys):
                    r.update(self.payload); break
            else:
                rows.append(dict(self.payload))
        class _R: pass
        res = _R(); res.data = [dict(r) for r in hit]
        return res


class _Not:
    def __init__(self, q): self.q = q
    def is_(self, col, val):
        assert val == "null"
        self.q.filters.append((col, "notnull", None)); return self.q


class FakeClient:
    def __init__(self, db): self.db = db
    def table(self, name): return _Q(self.db, name)


def make_db():
    return {
        "scenes": [
            {"id": "sc1", "script_id": "s1", "characters": ["MARCUS", "MARY"],
             "wardrobe": [{"name": "Trench coat", "character": "Marcus"}, "Hat"],
             "makeup": [{"requirements": "Scar", "character": "MARCUS"}]},
            {"id": "sc2", "script_id": "s1", "characters": ["Marcus"], "wardrobe": [], "makeup": []},
            {"id": "sc3", "script_id": "s1", "characters": ["MARY"], "wardrobe": [], "makeup": []},
        ],
        "casting": [{"id": "c1", "script_id": "s1", "character_name": "MARCUS"}],
        "department_items": [{"script_id": "s1", "item_type": "characters", "item_name": "MARCUS"}],
        "character_aliases": [],
    }


def rename(db, old, new):
    return svc.rename_character("s1", old, new, "u1", client=FakeClient(db))


def test_rename_rewrites_everything():
    db = make_db()
    out = rename(db, "marcus", "Detective Cole")
    assert out == {"character": "DETECTIVE COLE", "original_name": "MARCUS", "scenes_updated": 2}
    assert db["scenes"][0]["characters"] == ["DETECTIVE COLE", "MARY"]
    assert db["scenes"][1]["characters"] == ["DETECTIVE COLE"]
    assert db["scenes"][2]["characters"] == ["MARY"]
    assert db["scenes"][0]["wardrobe"] == [{"name": "Trench coat", "character": "DETECTIVE COLE"}, "Hat"]
    assert db["scenes"][0]["makeup"][0]["character"] == "DETECTIVE COLE"
    assert db["casting"][0]["character_name"] == "DETECTIVE COLE"
    assert db["department_items"][0]["item_name"] == "DETECTIVE COLE"
    assert db["character_aliases"] == [{
        "script_id": "s1", "alias": "MARCUS", "canonical_name": "DETECTIVE COLE",
        "original_name": "MARCUS", "merged_by": "u1"}]
    assert svc.original_names("s1", client=FakeClient(db)) == {"DETECTIVE COLE": "MARCUS"}


def test_chained_rename_keeps_script_original():
    db = make_db()
    rename(db, "MARCUS", "COLE")
    out = rename(db, "COLE", "REYES")
    assert out["original_name"] == "MARCUS"
    aliases = {a["alias"]: a for a in db["character_aliases"]}
    assert aliases["MARCUS"]["canonical_name"] == "REYES"   # old alias repointed
    assert aliases["COLE"]["canonical_name"] == "REYES"
    assert {a["original_name"] for a in aliases.values()} == {"MARCUS"}
    assert svc.original_names("s1", client=FakeClient(db)) == {"REYES": "MARCUS"}


def test_rename_back_to_original_clears_note_and_self_alias():
    db = make_db()
    rename(db, "MARCUS", "COLE")
    out = rename(db, "COLE", "MARCUS")
    assert out["original_name"] is None
    assert db["scenes"][0]["characters"] == ["MARCUS", "MARY"]
    assert all(a["alias"] != "MARCUS" for a in db["character_aliases"])  # no MARCUS->MARCUS
    assert svc.original_names("s1", client=FakeClient(db)) == {}


def test_merge_aliases_are_repointed_but_not_reported_as_original():
    db = make_db()
    db["character_aliases"].append(
        {"script_id": "s1", "alias": "MARKUS", "canonical_name": "MARCUS", "original_name": None})
    rename(db, "MARCUS", "COLE")
    markus = next(a for a in db["character_aliases"] if a["alias"] == "MARKUS")
    assert markus["canonical_name"] == "COLE"
    assert svc.original_names("s1", client=FakeClient(db)) == {"COLE": "MARCUS"}


def test_name_taken_by_another_character_is_rejected_and_nothing_changes():
    db = make_db()
    with pytest.raises(svc.NameTaken):
        rename(db, "MARCUS", "mary")
    assert db["scenes"][0]["characters"] == ["MARCUS", "MARY"]
    assert db["character_aliases"] == []


def test_unknown_character_and_bad_input():
    db = make_db()
    with pytest.raises(svc.CharacterNotFound):
        rename(db, "NOBODY", "X")
    with pytest.raises(svc.RenameError):
        rename(db, "MARCUS", "  ")
    with pytest.raises(svc.RenameError):
        rename(db, "MARCUS", "marcus")


def test_original_names_tolerates_missing_column():
    class Boom:
        def table(self, name): raise RuntimeError("column original_name does not exist")
    assert svc.original_names("s1", client=Boom()) == {}


# ---- route ----
def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def _auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)
    monkeypatch.setattr(cr, "get_user_id", lambda: "u1")


def test_route_requires_admin(monkeypatch, _auth):
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: "member")
    r = _client().post("/api/scripts/s1/characters/rename", json={"old_name": "A", "new_name": "B"})
    assert r.status_code == 403


@pytest.mark.parametrize("exc,code", [
    (svc.NameTaken("B"), 409), (svc.CharacterNotFound("A"), 404), (svc.RenameError("bad"), 400)])
def test_route_maps_errors(monkeypatch, _auth, exc, code):
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: "admin")
    def boom(*a, **k): raise exc
    monkeypatch.setattr(cr.rename_service, "rename_character", boom)
    r = _client().post("/api/scripts/s1/characters/rename", json={"old_name": "A", "new_name": "B"})
    assert r.status_code == code


def test_route_ok(monkeypatch, _auth):
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: "admin")
    monkeypatch.setattr(cr.rename_service, "rename_character",
                        lambda sid, o, n, uid: {"character": "B", "original_name": "A", "scenes_updated": 1})
    r = _client().post("/api/scripts/s1/characters/rename", json={"old_name": "A", "new_name": "B"})
    assert r.status_code == 200 and r.get_json()["original_name"] == "A"
