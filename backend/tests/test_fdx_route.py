import io
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services.screenplay_parser import ParsedScene
import routes.supabase_routes as sr


class _FakeQuery:
    def __init__(self, recorder, table):
        self.recorder = recorder; self.table = table
    def insert(self, rows):
        self.recorder.setdefault(self.table, []).extend(rows if isinstance(rows, list) else [rows])
        return self
    def execute(self):
        return None


class _FakeUpload:
    def upload(self, *args, **kwargs):
        return {}


class _FakeStorage:
    def from_(self, bucket):
        return _FakeUpload()


class _FakeSupabase:
    storage = _FakeStorage()

    def __init__(self):
        self.records = {}
    def table(self, name):
        return _FakeQuery(self.records, name)


def _scene(**kw):
    base = dict(
        scene_number_original="1", scene_order=1, int_ext="INT",
        setting="COFFEE SHOP", time_of_day="DAY", page_start=1, page_end=1,
        text_start=0, text_end=40, content_hash="abc123",
        scene_text="INT. COFFEE SHOP - DAY\nJohn sips.", location_hierarchy=["COFFEE SHOP"],
        speakers={"JOHN": 2}, shot_type=None, transitions=[], parse_method="fdx",
    )
    base.update(kw)
    return ParsedScene(**base)


def test_create_scenes_from_parsed_writes_fdx_records(monkeypatch):
    fake = _FakeSupabase()
    monkeypatch.setattr(sr, "supabase", fake)
    scenes = [_scene()]
    count, meta = sr.create_scenes_from_parsed(
        "script-1", scenes, "INT. COFFEE SHOP - DAY\nJohn sips.",
        [{"page_number": 1, "text": "INT. COFFEE SHOP - DAY\nJohn sips."}],
        {"parse_method": "fdx"},
    )
    assert count == 1
    assert meta["parse_method"] == "fdx"
    scene_rows = fake.records["scenes"]
    cand_rows = fake.records["scene_candidates"]
    assert len(scene_rows) == 1 and len(cand_rows) == 1
    assert scene_rows[0]["scene_number"] == "1"
    assert scene_rows[0]["speakers"] == ["JOHN"]          # scenes: list of names
    assert scene_rows[0]["parse_method"] == "fdx"
    assert scene_rows[0]["page_length_eighths"] >= 1
    assert cand_rows[0]["speaker_list"] == {"JOHN": 2}     # candidates: dict
    assert cand_rows[0]["status"] == "detected"


# Regression: a valid .fdx whose filename secure_filename() mangles (e.g. a
# non-ASCII base name that loses its extension) must still take the FDX branch,
# not fall through to pdfplumber ("No /Root object! - Is this really a PDF?").
_VALID_FDX = """<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Version="5">
  <Content>
    <Paragraph Type="Scene Heading" Number="1">
      <SceneProperties Length="1/8"/>
      <Text>INT. COFFEE SHOP - DAY</Text>
    </Paragraph>
    <Paragraph Type="Action"><Text>John sips his coffee.</Text></Paragraph>
    <Paragraph Type="Character"><Text>JOHN</Text></Paragraph>
    <Paragraph Type="Dialogue"><Text>Morning.</Text></Paragraph>
  </Content>
</FinalDraft>
"""


@pytest.mark.parametrize("filename", ["剧本.fdx", "The Late Shift.fdx"])
def test_upload_fdx_takes_fdx_branch_regardless_of_filename(monkeypatch, filename):
    try:
        import app as app_module
    except Exception:
        pytest.skip("Flask app requires env vars not present in this environment")

    monkeypatch.setattr(sr, "supabase", _FakeSupabase())
    client = app_module.app.test_client()

    data = {"file": (io.BytesIO(_VALID_FDX.encode("utf-8")), filename)}
    resp = client.post("/api/upload", data=data, content_type="multipart/form-data")

    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["parse_method"] == "fdx"
    assert body["scene_candidates"] == 1


def test_store_fdx_preview_uploads_and_updates(monkeypatch, tmp_path):
    import routes.supabase_routes as sr

    # Fake supabase that records inserts/updates/uploads and returns scenes.
    calls = {"uploads": [], "script_updates": [], "scene_updates": []}

    class Q:
        def __init__(self, table): self.table = table; self._filter = None
        def select(self, *a, **k): return self
        def eq(self, *a, **k): self._filter = a; return self
        def order(self, *a, **k): return self
        def execute(self):
            if self.table == "scenes":
                class R: data = [{"id": "s1", "scene_order": 1},
                                 {"id": "s2", "scene_order": 2}]
                return R()
            class R: data = []
            return R()
        def update(self, payload):
            (calls["script_updates"] if self.table == "scripts"
             else calls["scene_updates"]).append((self.table, payload))
            return self

    class Up:
        def upload(self, path, content, opts):
            calls["uploads"].append((path, opts)); return {}
    class St:
        def from_(self, b): return Up()
    class FS:
        storage = St()
        def table(self, name): return Q(name)

    monkeypatch.setattr(sr, "supabase", FS())
    monkeypatch.setattr(
        "services.fdx_preview.generate_fdx_preview_pdf",
        lambda fdx_path, rows: (b"%PDF-fake", {"s1": 1, "s2": 2}),
    )

    fdx = tmp_path / "x.fdx"; fdx.write_text("<FinalDraft/>", encoding="utf-8")
    path = sr.store_fdx_preview("script-9", str(fdx))

    assert path == "script-9/preview.pdf"
    assert calls["uploads"] and calls["uploads"][0][0] == "script-9/preview.pdf"
    assert calls["uploads"][0][1].get("content-type") == "application/pdf"
    # preview_pdf_path recorded on the script
    assert any(p.get("preview_pdf_path") == "script-9/preview.pdf"
               for _, p in calls["script_updates"])
    # both scenes got page_start updated to the generated pages
    starts = [p.get("page_start") for _, p in calls["scene_updates"]]
    assert 1 in starts and 2 in starts


def test_get_pdf_url_prefers_preview_path(monkeypatch):
    import routes.supabase_routes as sr
    import middleware.authorization as authz
    try:
        import app as app_module
    except Exception:
        import pytest; pytest.skip("Flask app requires env vars")

    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: "owner")

    class Q:
        def __init__(self, table): self.table = table
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def single(self): return self
        def execute(self):
            class R: data = {"file_path": "sid/orig.fdx", "file_name": "orig.fdx",
                             "title": "T", "preview_pdf_path": "sid/preview.pdf"}
            return R()
    class Signed:
        def create_signed_url(self, path, ttl):
            return {"signedURL": f"https://signed/{path}"}
    class St:
        def from_(self, b): return Signed()
    class FS:
        storage = St()
        def table(self, name): return Q(name)

    monkeypatch.setattr(sr, "supabase", FS())
    client = app_module.app.test_client()
    r = client.get("/api/scripts/sid/pdf-url")
    assert r.status_code == 200
    assert r.get_json()["pdf_url"] == "https://signed/sid/preview.pdf"


def test_get_pdf_url_lazy_generates_for_fdx(monkeypatch):
    import routes.supabase_routes as sr
    import middleware.authorization as authz
    try:
        import app as app_module
    except Exception:
        import pytest; pytest.skip("Flask app requires env vars")

    monkeypatch.setattr(authz, "get_script_role", lambda sid, uid: "owner")

    signed = {}
    class Q:
        def __init__(self, table): self.table = table
        def select(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def single(self): return self
        def execute(self):
            class R: data = {"file_path": "sid/orig.fdx", "file_name": "orig.fdx",
                             "title": "T", "preview_pdf_path": None}
            return R()
    class Signed:
        def create_signed_url(self, path, ttl):
            signed["path"] = path
            return {"signedURL": f"https://signed/{path}"}
    class St:
        def from_(self, b): return Signed()
    class FS:
        storage = St()
        def table(self, name): return Q(name)

    monkeypatch.setattr(sr, "supabase", FS())
    monkeypatch.setattr(sr, "_lazy_generate_fdx_preview",
                        lambda script_id, fdx_path: "sid/preview.pdf")
    client = app_module.app.test_client()
    r = client.get("/api/scripts/sid/pdf-url")
    assert r.status_code == 200
    assert signed["path"] == "sid/preview.pdf"
