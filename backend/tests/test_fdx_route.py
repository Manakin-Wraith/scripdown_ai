import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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


class _FakeSupabase:
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
