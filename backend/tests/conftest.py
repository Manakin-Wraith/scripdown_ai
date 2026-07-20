import pytest


class FakeTable:
    """Minimal chainable stand-in for supabase-py's query builder."""
    def __init__(self, rows):
        self._rows = rows
        self._filters = {}

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def limit(self, _n):
        return self

    def single(self):
        self._single = True
        return self

    def execute(self):
        data = [r for r in self._rows
                if all(r.get(k) == v for k, v in self._filters.items())]
        if getattr(self, "_single", False):
            return type("Res", (), {"data": data[0] if data else None})()
        return type("Res", (), {"data": data})()


class FakeSupabase:
    def __init__(self, tables=None):
        self._tables = tables or {}

    def set_table(self, name, rows):
        self._tables[name] = rows

    def table(self, name):
        return FakeTable(self._tables.get(name, []))


@pytest.fixture
def fake_supabase():
    return FakeSupabase()
