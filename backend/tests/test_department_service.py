import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.department_service as ds


class _Resp:
    def __init__(self, data): self.data = data


class _FakeTable:
    def __init__(self, rows): self._rows = rows
    def select(self, *_a, **_k): return self
    def order(self, *_a, **_k): return self
    def execute(self): return _Resp(self._rows)


class _FakeSupabase:
    def __init__(self, rows): self._rows = rows
    def table(self, _n): return _FakeTable(self._rows)


def test_list_and_helpers(monkeypatch):
    ds._reset_departments_cache()
    rows = [{"code": "camera", "name": "Camera", "color": "#111"},
            {"code": "grip", "name": "Grip", "color": "#222"}]
    monkeypatch.setattr(ds, "get_supabase_admin", lambda: _FakeSupabase(rows))

    assert [d["code"] for d in ds.get_departments_list()] == ["camera", "grip"]
    assert ds.get_department_name("grip") == "Grip"
    assert ds.get_department_name("nope") == "nope"
    assert ds.valid_department_codes() == {"camera", "grip"}


def test_read_failure_returns_empty(monkeypatch):
    ds._reset_departments_cache()
    def boom(): raise RuntimeError("db down")
    monkeypatch.setattr(ds, "get_supabase_admin", lambda: (_ for _ in ()).throw(RuntimeError("x")))
    assert ds.get_departments_list() == []
