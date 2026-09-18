import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.revision_service as rs


# ---------------------------------------------------------------------------
# Fake supabase client — supports the chain calls revision_service actually
# uses: select/insert/update, eq, lt, order(desc=...), limit, single.
# ---------------------------------------------------------------------------

class FakeTable:
    def __init__(self, store, name):
        self.store, self.name = store, name
        self._filters = []
        self._lt = []
        self._order = None
        self._limit = None
        self._single = False
        self._op = 'select'
        self._payload = None

    def select(self, *a, **k):
        self._op = 'select'
        return self

    def insert(self, payload):
        self._op, self._payload = 'insert', payload
        return self

    def update(self, payload):
        self._op, self._payload = 'update', payload
        return self

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def lt(self, col, val):
        self._lt.append((col, val))
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def single(self):
        self._single = True
        return self

    def _match(self, row):
        for c, v in self._filters:
            if row.get(c) != v:
                return False
        for c, v in self._lt:
            if row.get(c) is None or not (row.get(c) < v):
                return False
        return True

    def execute(self):
        rows = self.store.setdefault(self.name, [])

        if self._op == 'insert':
            payload = self._payload if isinstance(self._payload, list) else [self._payload]
            out = []
            for p in payload:
                p = dict(p)
                p.setdefault('id', f"{self.name}-{len(rows) + 1}")
                rows.append(p)
                out.append(p)
            return type("R", (), {"data": out})()

        if self._op == 'update':
            hit = [r for r in rows if self._match(r)]
            for r in hit:
                r.update(self._payload)
            return type("R", (), {"data": hit})()

        # select
        data = [r for r in rows if self._match(r)]
        if self._order:
            col, desc = self._order
            data = sorted(data, key=lambda r: r.get(col), reverse=desc)
        if self._limit is not None:
            data = data[:self._limit]
        if self._single:
            return type("R", (), {"data": data[0] if data else None})()
        return type("R", (), {"data": data})()


class FakeClient:
    def __init__(self, store=None):
        self.store = store if store is not None else {}

    def table(self, name):
        return FakeTable(self.store, name)


# ---------------------------------------------------------------------------
# calculate_text_similarity
# ---------------------------------------------------------------------------

def test_similarity_identical_text_is_one():
    assert rs.calculate_text_similarity("the quick fox", "the quick fox") == 1.0


def test_similarity_disjoint_text_is_zero():
    assert rs.calculate_text_similarity("apples oranges", "bananas grapes") == 0.0


def test_similarity_partial_overlap():
    score = rs.calculate_text_similarity("the quick brown fox", "the quick red fox")
    # 4 shared words (the, quick, fox... "red"/"brown" differ) out of 5 union
    assert 0.0 < score < 1.0


def test_similarity_empty_strings_are_zero():
    assert rs.calculate_text_similarity("", "something") == 0.0
    assert rs.calculate_text_similarity("something", "") == 0.0


# ---------------------------------------------------------------------------
# match_scenes_by_header
# ---------------------------------------------------------------------------

def test_match_exact_scene_number():
    old = [{"scene_number": "1", "int_ext": "INT", "setting": "KITCHEN", "time_of_day": "DAY"}]
    new = [{"id": "n1", "scene_number": "1", "int_ext": "INT", "setting": "KITCHEN", "time_of_day": "DAY"}]
    matches = rs.match_scenes_by_header(old, new)
    assert matches["n1"] == old[0]


def test_match_falls_back_to_fuzzy_header_similarity():
    old = [{"scene_number": "1", "int_ext": "INT", "setting": "KITCHEN", "time_of_day": "DAY"}]
    # Renumbered from 1 -> 1A but same header text, should still fuzzy-match.
    new = [{"id": "n1", "scene_number": "1A", "int_ext": "INT", "setting": "KITCHEN", "time_of_day": "DAY"}]
    matches = rs.match_scenes_by_header(old, new)
    assert matches["n1"] == old[0]


def test_match_returns_none_when_nothing_similar_enough():
    old = [{"scene_number": "1", "int_ext": "INT", "setting": "KITCHEN", "time_of_day": "DAY"}]
    new = [{"id": "n1", "scene_number": "9", "int_ext": "EXT", "setting": "DESERT", "time_of_day": "NIGHT"}]
    matches = rs.match_scenes_by_header(old, new)
    assert matches["n1"] is None


# ---------------------------------------------------------------------------
# compare_scene_content
# ---------------------------------------------------------------------------

def test_compare_identical_scenes_no_changes():
    scene = {"int_ext": "INT", "setting": "KITCHEN", "time_of_day": "DAY", "full_text": "Hello there."}
    has_changes, changes = rs.compare_scene_content(scene, dict(scene))
    assert has_changes is False
    assert changes == []


def test_compare_detects_header_and_content_changes():
    old = {"int_ext": "INT", "setting": "KITCHEN", "time_of_day": "DAY", "full_text": "Hello there."}
    new = {"int_ext": "EXT", "setting": "GARDEN", "time_of_day": "NIGHT", "full_text": "Goodbye now."}
    has_changes, changes = rs.compare_scene_content(old, new)
    assert has_changes is True
    assert any("INT/EXT" in c for c in changes)
    assert any("Setting changed" in c for c in changes)
    assert any("Time changed" in c for c in changes)
    assert any("content modified" in c.lower() for c in changes)


# ---------------------------------------------------------------------------
# diff_script_versions
# ---------------------------------------------------------------------------

def _scene(number, setting="KITCHEN", text="Some dialogue happens here today."):
    """An existing DB scene — always carries an id."""
    return {
        "id": f"old-{number}",
        "scene_number": number,
        "int_ext": "INT",
        "setting": setting,
        "time_of_day": "DAY",
        "full_text": text,
    }


def _new_scene(number, setting="KITCHEN", text="Some dialogue happens here today."):
    """A freshly-parsed scene from extract_scenes_from_pdf — no id key,
    same as the real extraction pipeline produces."""
    return {
        "scene_number": number,
        "int_ext": "INT",
        "setting": setting,
        "time_of_day": "DAY",
        "full_text": text,
    }


def test_diff_marks_unchanged_scene():
    old = [_scene("1")]
    new = [_new_scene("1")]
    diffs = rs.diff_script_versions(old, new)
    assert len(diffs) == 1
    assert diffs[0].change_type == rs.ChangeType.UNCHANGED


def test_diff_marks_modified_scene():
    old = [_scene("1", setting="KITCHEN")]
    new = [_new_scene("1", setting="GARDEN")]
    diffs = rs.diff_script_versions(old, new)
    assert len(diffs) == 1
    assert diffs[0].change_type == rs.ChangeType.MODIFIED
    assert any("Setting changed" in c for c in diffs[0].changes)


def test_diff_marks_added_scene():
    old = [_scene("1")]
    new = [_new_scene("1"), _new_scene("2", setting="DESERT")]
    diffs = rs.diff_script_versions(old, new)
    added = [d for d in diffs if d.change_type == rs.ChangeType.ADDED]
    assert len(added) == 1
    assert added[0].scene_number == "2"


def test_diff_marks_removed_scene():
    old = [_scene("1"), _scene("2")]
    new = [_new_scene("1")]
    diffs = rs.diff_script_versions(old, new)
    removed = [d for d in diffs if d.change_type == rs.ChangeType.REMOVED]
    assert len(removed) == 1
    assert removed[0].scene_number == "2"


def test_diff_sorts_by_numeric_scene_number_with_alpha_suffix():
    old = []
    new = [_new_scene("10"), _new_scene("2"), _new_scene("2A")]
    diffs = rs.diff_script_versions(old, new)
    assert [d.scene_number for d in diffs] == ["2", "2A", "10"]


# ---------------------------------------------------------------------------
# create_version_record
# ---------------------------------------------------------------------------

def test_create_version_record_starts_at_one():
    client = FakeClient()
    version = rs.create_version_record(client, "s1", "blue", notes="first pass")
    assert version["version_number"] == 1
    assert version["revision_color"] == "blue"
    assert version["notes"] == "first pass"


def test_create_version_record_increments_from_existing():
    client = FakeClient()
    client.store["script_versions"] = [
        {"id": "v1", "script_id": "s1", "version_number": 1},
        {"id": "v2", "script_id": "s1", "version_number": 2},
    ]
    version = rs.create_version_record(client, "s1", "pink")
    assert version["version_number"] == 3


# ---------------------------------------------------------------------------
# apply_revision_changes
# ---------------------------------------------------------------------------

def test_apply_added_scene_inserts_row_and_history():
    client = FakeClient()
    diff = rs.SceneDiff(
        change_type=rs.ChangeType.ADDED,
        scene_number="3",
        new_scene={"scene_number": "3", "int_ext": "INT", "setting": "HALL",
                   "time_of_day": "DAY", "full_text": "text", "page_start": 1,
                   "page_end": 1, "content_hash": "h1"},
    )
    stats = rs.apply_revision_changes(client, "s1", "v1", [diff], [])
    assert stats == {"added": 1, "modified": 0, "removed": 0, "unchanged": 0}
    assert len(client.store["scenes"]) == 1
    assert client.store["scenes"][0]["revision_number"] == 1
    assert len(client.store["scene_history"]) == 1
    assert client.store["scene_history"][0]["change_type"] == "created"


def test_apply_modified_scene_updates_row_bumps_revision_and_records_previous():
    client = FakeClient()
    client.store["scenes"] = [
        {"id": "sc1", "script_id": "s1", "int_ext": "INT", "setting": "KITCHEN",
         "time_of_day": "DAY", "full_text": "old text", "content_hash": "old",
         "revision_number": 1},
    ]
    diff = rs.SceneDiff(
        change_type=rs.ChangeType.MODIFIED,
        scene_number="1",
        old_scene=client.store["scenes"][0],
        new_scene={"int_ext": "INT", "setting": "GARDEN", "time_of_day": "DAY",
                   "full_text": "new text", "page_start": 1, "page_end": 2,
                   "content_hash": "new"},
    )
    stats = rs.apply_revision_changes(client, "s1", "v1", [diff], [])
    assert stats["modified"] == 1
    updated = client.store["scenes"][0]
    assert updated["setting"] == "GARDEN"
    assert updated["revision_number"] == 2
    history = client.store["scene_history"][0]
    assert history["change_type"] == "modified"
    assert history["previous_data"]["setting"] == "KITCHEN"


def test_apply_removed_scene_marks_omitted_not_deleted():
    client = FakeClient()
    client.store["scenes"] = [
        {"id": "sc1", "script_id": "s1", "is_omitted": False},
    ]
    diff = rs.SceneDiff(
        change_type=rs.ChangeType.REMOVED,
        scene_number="1",
        old_scene=client.store["scenes"][0],
    )
    stats = rs.apply_revision_changes(client, "s1", "v1", [diff], [])
    assert stats["removed"] == 1
    # Still present in the table — soft-deleted, not dropped.
    assert len(client.store["scenes"]) == 1
    assert client.store["scenes"][0]["is_omitted"] is True
    assert client.store["scene_history"][0]["change_type"] == "omitted"


def test_apply_unchanged_scene_writes_nothing():
    client = FakeClient()
    diff = rs.SceneDiff(change_type=rs.ChangeType.UNCHANGED, scene_number="1")
    stats = rs.apply_revision_changes(client, "s1", "v1", [diff], [])
    assert stats["unchanged"] == 1
    assert client.store.get("scenes", []) == []
    assert client.store.get("scene_history", []) == []


# ---------------------------------------------------------------------------
# get_version_history / get_version_diff
# ---------------------------------------------------------------------------

def test_get_version_history_orders_newest_first():
    client = FakeClient()
    client.store["script_versions"] = [
        {"id": "v1", "script_id": "s1", "version_number": 1},
        {"id": "v2", "script_id": "s1", "version_number": 2},
    ]
    history = rs.get_version_history(client, "s1")
    assert [v["version_number"] for v in history] == [2, 1]


def test_get_version_diff_compares_to_previous_by_default():
    client = FakeClient()
    client.store["script_versions"] = [
        {"id": "v1", "script_id": "s1", "version_number": 1},
        {"id": "v2", "script_id": "s1", "version_number": 2},
    ]
    client.store["scene_history"] = [
        {"id": "h1", "version_id": "v2", "change_type": "modified"},
        {"id": "h2", "version_id": "v1", "change_type": "created"},
    ]
    diff = rs.get_version_diff(client, "s1", "v2")
    assert [d["id"] for d in diff] == ["h1"]


def test_get_version_diff_returns_empty_when_no_prior_version():
    client = FakeClient()
    client.store["script_versions"] = [
        {"id": "v1", "script_id": "s1", "version_number": 1},
    ]
    assert rs.get_version_diff(client, "s1", "v1") == []


def test_get_version_diff_returns_empty_for_missing_version():
    client = FakeClient()
    assert rs.get_version_diff(client, "s1", "missing") == []


# ---------------------------------------------------------------------------
# extract_scenes_from_pdf
# ---------------------------------------------------------------------------

def test_extract_scenes_from_pdf_groups_pages_into_scenes(monkeypatch):
    from services.extraction_pipeline import PageData

    pages = [
        PageData(page_number=1, text="INT. KITCHEN - DAY\nAction here.",
                 content_hash="h1", has_scene_header=True,
                 scene_headers=[{"scene_number": "1", "int_ext": "INT",
                                 "setting": "KITCHEN", "time_of_day": "DAY"}]),
        PageData(page_number=2, text="More action.", content_hash="h2"),
        PageData(page_number=3, text="EXT. GARDEN - NIGHT\nOutside now.",
                 content_hash="h3", has_scene_header=True,
                 scene_headers=[{"scene_number": "2", "int_ext": "EXT",
                                 "setting": "GARDEN", "time_of_day": "NIGHT"}]),
    ]
    monkeypatch.setattr(rs, "parse_pdf_with_pages", lambda path: (pages, "full text"))

    scenes = rs.extract_scenes_from_pdf("fake.pdf")

    assert [s["scene_number"] for s in scenes] == ["1", "2"]
    assert scenes[0]["page_start"] == 1
    assert scenes[0]["page_end"] == 2
    assert scenes[1]["page_start"] == 3
    assert scenes[1]["page_end"] == 3
    assert scenes[1]["content_hash"]
