# backend/tests/test_casting_photos.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import io
import pytest
import services.casting_service as casting_service
import services.casting_service as cs
import routes.casting_routes as cr
import middleware.authorization as authz

PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "3dde0000000c49444154089963f8cf0000000000010001a3aa2f06000000004"
    "9454e44ae426082")


# --- service-level fake DB + storage (extends test_casting_service.py pattern) ---
class FakeTable:
    def __init__(self, store, name):
        self.store, self.name, self._filters, self._payload, self._op = store, name, [], None, None
    def select(self, *a, **k): self._op = 'select'; return self
    def insert(self, payload): self._op, self._payload = 'insert', payload; return self
    def update(self, payload): self._op, self._payload = 'update', payload; return self
    def delete(self): self._op = 'delete'; return self
    def eq(self, col, val): self._filters.append((col, val)); return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def _match(self, row): return all(row.get(c) == v for c, v in self._filters)
    def execute(self):
        rows = self.store.setdefault(self.name, [])
        if self._op == 'select':
            return type("R", (), {"data": [r for r in rows if self._match(r)]})
        if self._op == 'insert':
            payload = self._payload if isinstance(self._payload, list) else [self._payload]
            for p in payload:
                p.setdefault('id', f"{self.name}-{len(rows)+1}")
                rows.append(p)
            return type("R", (), {"data": payload})
        if self._op == 'update':
            hit = [r for r in rows if self._match(r)]
            for r in hit: r.update(self._payload)
            return type("R", (), {"data": hit})
        if self._op == 'delete':
            hit = [r for r in rows if self._match(r)]
            self.store[self.name] = [r for r in rows if not self._match(r)]
            return type("R", (), {"data": hit})


class _FakeBucket:
    def upload(self, *a, **k): return None
    def remove(self, *a, **k): return None
    def create_signed_url(self, *a, **k): return {"signedURL": "https://signed/photo"}


class _FakeStorage:
    def from_(self, bucket): return _FakeBucket()


class FakeClient:
    def __init__(self, store): self.store = store
    def table(self, name): return FakeTable(self.store, name)
    @property
    def storage(self): return _FakeStorage()


@pytest.fixture
def mock_client(monkeypatch):
    store = {"casting": [], "casting_unavailability": [], "casting_photos": []}
    monkeypatch.setattr(cs, "_client", lambda: FakeClient(store))
    return store


@pytest.fixture
def seed_casting(mock_client):
    return cs.create_casting("s1", "JOHN", "u1")


class TestPhotoService:
    def test_store_and_list_photo(self, mock_client, seed_casting):
        photo = casting_service.store_photo(
            seed_casting["id"], seed_casting["script_id"],
            "full_body", PNG_1PX, "image/png")
        assert photo["kind"] == "full_body"
        assert photo["url"]  # signed URL present
        photos = casting_service.list_photos(seed_casting["id"])
        assert [p["id"] for p in photos] == [photo["id"]]

    def test_store_photo_rejects_bad_type(self, mock_client, seed_casting):
        with pytest.raises(ValueError):
            casting_service.store_photo(
                seed_casting["id"], seed_casting["script_id"],
                "other", b"x", "application/pdf")

    def test_store_photo_rejects_bad_kind(self, mock_client, seed_casting):
        with pytest.raises(ValueError):
            casting_service.store_photo(
                seed_casting["id"], seed_casting["script_id"],
                "portrait", PNG_1PX, "image/png")

    def test_serialize_includes_photos(self, mock_client, seed_casting):
        casting_service.store_photo(
            seed_casting["id"], seed_casting["script_id"],
            "full_body", PNG_1PX, "image/png")
        row = casting_service.get_casting(seed_casting["id"])
        out = casting_service.serialize(row, include_contact=False)
        assert len(out["photos"]) == 1

    def test_delete_photo(self, mock_client, seed_casting):
        photo = casting_service.store_photo(
            seed_casting["id"], seed_casting["script_id"],
            "other", PNG_1PX, "image/png")
        removed = casting_service.delete_photo(photo["id"])
        assert removed["id"] == photo["id"]
        assert casting_service.list_photos(seed_casting["id"]) == []
        assert casting_service.delete_photo("nope") is None


# --- route-level (extends test_casting_routes.py pattern) ---
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


class TestPhotoRoutes:
    def test_upload_requires_admin(self, monkeypatch):
        _as_role(monkeypatch, "viewer")
        monkeypatch.setattr(authz, "_lookup_script_id", lambda *a, **k: "s1")
        r = _client().post(
            "/api/casting/c1/photos?kind=full_body",
            data={"file": (io.BytesIO(PNG_1PX), "x.png")},
            content_type="multipart/form-data")
        assert r.status_code == 403

    def test_upload_requires_auth(self, monkeypatch):
        monkeypatch.setattr("middleware.auth.DEV_MODE", False)
        r = _client().post(
            "/api/casting/c1/photos?kind=full_body",
            data={"file": (io.BytesIO(PNG_1PX), "x.png")},
            content_type="multipart/form-data")
        assert r.status_code == 401

    def test_upload_then_delete(self, monkeypatch):
        _as_role(monkeypatch, "admin")
        monkeypatch.setattr(authz, "_lookup_script_id", lambda *a, **k: "s1")
        photos = []
        monkeypatch.setattr(cr.casting_service, "get_casting",
                            lambda cid: {"id": cid, "script_id": "s1", "character_name": "JOHN"})

        def _store(cid, sid, kind, blob, ct):
            p = {"id": "p1", "kind": kind, "caption": None, "sort_order": 0,
                 "url": "https://signed/p1.png"}
            photos.append(p)
            return p

        monkeypatch.setattr(cr.casting_service, "store_photo", _store)
        monkeypatch.setattr(cr.casting_service, "delete_photo",
                            lambda pid: photos.clear())
        monkeypatch.setattr(cr.casting_service, "list_photos", lambda cid: list(photos))

        up = _client().post(
            "/api/casting/c1/photos?kind=full_body",
            data={"file": (io.BytesIO(PNG_1PX), "x.png")},
            content_type="multipart/form-data")
        assert up.status_code == 201
        pid = up.get_json()["photo"]["id"]
        d = _client().delete(f"/api/casting/photos/{pid}")
        assert d.status_code == 200
        assert cr.casting_service.list_photos("c1") == []

    def test_upload_rejects_wrong_type(self, monkeypatch):
        _as_role(monkeypatch, "admin")
        monkeypatch.setattr(authz, "_lookup_script_id", lambda *a, **k: "s1")
        r = _client().post(
            "/api/casting/c1/photos?kind=other",
            data={"file": (io.BytesIO(b"GIF89a"), "x.gif", "image/gif")},
            content_type="multipart/form-data")
        assert r.status_code == 400
