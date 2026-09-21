import pytest
import sys
from unittest.mock import patch, MagicMock


# Patch the supabase create_client before any imports happen
# This allows tests to run with dummy env vars without connection errors
def pytest_configure(config):
    """Patch supabase.create_client to avoid real connection attempts during tests."""
    from supabase import create_client as real_create_client

    def mock_create_client(url, key, options=None):
        """Mock that returns a MagicMock instead of trying to connect."""
        return MagicMock()

    # Patch it in the supabase module itself
    import supabase
    supabase.create_client = mock_create_client


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
