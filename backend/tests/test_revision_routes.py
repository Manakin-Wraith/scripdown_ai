import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import io
import pytest

import routes.supabase_routes as sr
import services.revision_service as rs
import middleware.authorization as authz


def _client():
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture(autouse=True)
def _bypass_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", True)


def _as_role(monkeypatch, role):
    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: role)


class FakeScenesTable:
    """Just enough of the query builder for the `scenes` select in
    import_revision: .select().eq('script_id', ...).order(...).execute()."""
    def __init__(self, rows):
        self._rows = rows
        self._script_id = None

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        if col == 'script_id':
            self._script_id = val
        return self

    def order(self, *a, **k):
        return self

    def execute(self):
        data = [r for r in self._rows if r.get('script_id') == self._script_id]
        return type("R", (), {"data": data})()


class FakeSupabase:
    def __init__(self, scenes=None):
        self._scenes = scenes or []

    def table(self, name):
        assert name == 'scenes', f"import_revision only queries scenes directly, got {name}"
        return FakeScenesTable(self._scenes)


def _pdf_file(name="revision.pdf"):
    return {"file": (io.BytesIO(b"%PDF-1.4 fake"), name)}


# ---------------------------------------------------------------------------
# Auth / authorization
# ---------------------------------------------------------------------------

def test_import_revision_requires_auth(monkeypatch):
    monkeypatch.setattr("middleware.auth.DEV_MODE", False)
    resp = _client().post(
        "/api/scripts/s1/versions/import",
        data=_pdf_file(), content_type="multipart/form-data",
    )
    assert resp.status_code == 401


def test_import_revision_forbidden_for_viewer(monkeypatch):
    _as_role(monkeypatch, "viewer")
    resp = _client().post(
        "/api/scripts/s1/versions/import",
        data=_pdf_file(), content_type="multipart/form-data",
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_import_revision_missing_file_returns_400(monkeypatch):
    _as_role(monkeypatch, "member")
    monkeypatch.setattr(sr, "supabase", FakeSupabase())
    resp = _client().post(
        "/api/scripts/s1/versions/import",
        data={}, content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "file" in resp.get_json()["error"].lower()


def test_import_revision_rejects_non_pdf(monkeypatch):
    _as_role(monkeypatch, "member")
    monkeypatch.setattr(sr, "supabase", FakeSupabase())
    resp = _client().post(
        "/api/scripts/s1/versions/import",
        data=_pdf_file(name="revision.fdx"), content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "pdf" in resp.get_json()["error"].lower()


# ---------------------------------------------------------------------------
# Preview vs. apply behavior
# ---------------------------------------------------------------------------

def test_import_revision_preview_mode_does_not_write(monkeypatch):
    _as_role(monkeypatch, "member")
    monkeypatch.setattr(sr, "supabase", FakeSupabase(scenes=[
        {"id": "sc1", "script_id": "s1", "scene_number": "1",
         "int_ext": "INT", "setting": "KITCHEN", "time_of_day": "DAY"},
    ]))
    monkeypatch.setattr(rs, "extract_scenes_from_pdf", lambda path: [
        {"scene_number": "1", "int_ext": "INT", "setting": "KITCHEN", "time_of_day": "DAY"},
        {"scene_number": "2", "int_ext": "EXT", "setting": "DESERT", "time_of_day": "NIGHT"},
    ])

    applied = {"called": False}
    def _boom_if_called(*a, **k):
        applied["called"] = True
        raise AssertionError("apply_revision_changes must not run in preview mode")
    monkeypatch.setattr(rs, "apply_revision_changes", _boom_if_called)
    monkeypatch.setattr(rs, "create_version_record", _boom_if_called)

    resp = _client().post(
        "/api/scripts/s1/versions/import",
        data={**_pdf_file(), "apply_changes": "false"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["preview"] is True
    assert body["diff_summary"]["added"] == 1  # scene 2 is new
    assert applied["called"] is False


def test_import_revision_apply_mode_creates_version_and_applies(monkeypatch):
    _as_role(monkeypatch, "member")
    monkeypatch.setattr(sr, "supabase", FakeSupabase(scenes=[
        {"id": "sc1", "script_id": "s1", "scene_number": "1"},
    ]))
    monkeypatch.setattr(rs, "extract_scenes_from_pdf", lambda path: [
        {"scene_number": "1"}, {"scene_number": "2"},
    ])
    monkeypatch.setattr(rs, "create_version_record",
                         lambda supa, sid, color, pdf_path=None, notes=None:
                         {"id": "v1", "version_number": 1, "revision_color": color})

    calls = {}
    def _apply(supa, sid, version_id, diffs, new_scenes):
        calls["version_id"] = version_id
        calls["diff_count"] = len(diffs)
        return {"added": 1, "modified": 0, "removed": 0, "unchanged": 0}
    monkeypatch.setattr(rs, "apply_revision_changes", _apply)

    resp = _client().post(
        "/api/scripts/s1/versions/import",
        data={**_pdf_file(), "revision_color": "pink", "apply_changes": "true"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["version"]["id"] == "v1"
    assert body["applied_stats"]["added"] == 1
    assert calls["version_id"] == "v1"


def test_import_revision_apply_mode_failed_version_returns_500(monkeypatch):
    _as_role(monkeypatch, "member")
    monkeypatch.setattr(sr, "supabase", FakeSupabase(scenes=[]))
    monkeypatch.setattr(rs, "extract_scenes_from_pdf", lambda path: [])
    monkeypatch.setattr(rs, "create_version_record",
                         lambda supa, sid, color, pdf_path=None, notes=None: None)

    resp = _client().post(
        "/api/scripts/s1/versions/import",
        data={**_pdf_file(), "apply_changes": "true"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /versions, /versions/<id>, /versions/<id>/diff — smoke coverage
# ---------------------------------------------------------------------------

class FakeVersionsSupabase:
    """Minimal chainable stub for the plain select() calls these GET
    endpoints issue directly against `supabase`."""
    def __init__(self, versions=None, history=None):
        self._versions = versions or []
        self._history = history or []

    def table(self, name):
        rows = self._versions if name == 'script_versions' else self._history
        return _ChainTable(rows)


class _ChainTable:
    def __init__(self, rows):
        self._rows, self._filters, self._single = rows, [], False

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def order(self, *a, **k):
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        data = [r for r in self._rows if all(r.get(c) == v for c, v in self._filters)]
        if self._single:
            return type("R", (), {"data": data[0] if data else None})()
        return type("R", (), {"data": data})()


def test_get_script_versions_returns_list(monkeypatch):
    _as_role(monkeypatch, "member")
    monkeypatch.setattr(sr, "supabase", FakeVersionsSupabase(versions=[
        {"id": "v1", "script_id": "s1", "version_number": 1},
    ]))
    resp = _client().get("/api/scripts/s1/versions")
    assert resp.status_code == 200
    assert resp.get_json()["total"] == 1


def test_get_script_versions_forbidden_for_viewer(monkeypatch):
    _as_role(monkeypatch, "viewer")
    resp = _client().get("/api/scripts/s1/versions")
    assert resp.status_code == 403


def test_get_version_details_404_when_missing(monkeypatch):
    _as_role(monkeypatch, "member")
    monkeypatch.setattr(sr, "supabase", FakeVersionsSupabase(versions=[]))
    resp = _client().get("/api/scripts/s1/versions/missing")
    assert resp.status_code == 404
