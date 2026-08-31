"""GET /api/scripts: production_id / production_title enrichment."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routes.supabase_routes as sr


class FakeQuery:
    def __init__(self, rows):
        self._rows = list(rows)
        self._single = False

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._rows = [r for r in self._rows if r.get(col) == val]
        return self

    def in_(self, col, values):
        values = set(values)
        self._rows = [r for r in self._rows if r.get(col) in values]
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        if self._single:
            return SimpleNamespace(data=self._rows[0] if self._rows else None)
        return SimpleNamespace(data=self._rows)


class FakeSupabase:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return FakeQuery(self.tables.get(name, []))


def test_attach_production_info_sets_id_and_title():
    supa = FakeSupabase({
        "productions": [{"id": "p1", "title": "Farm Feature"}],
    })
    sr.supabase = supa
    scripts = [
        {"id": "s1", "production_id": "p1"},
        {"id": "s2", "production_id": None},
    ]
    out = sr._attach_production_info(scripts)
    assert out[0]["production_id"] == "p1"
    assert out[0]["production_title"] == "Farm Feature"
    assert out[1]["production_id"] is None
    assert out[1]["production_title"] is None
