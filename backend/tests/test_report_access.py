"""Owner-or-member access checks for report endpoints."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.report_access import script_access, report_script_id


class _FakeResp:
    def __init__(self, data): self.data = data


class _FakeQ:
    def __init__(self, rows): self._rows = rows
    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def execute(self): return _FakeResp(self._rows)


class _FakeClient:
    def __init__(self, scripts=None, members=None, reports=None):
        self._t = {
            'scripts': scripts or [],
            'script_members': members or [],
            'reports': reports or [],
        }
    def table(self, name): return _FakeQ(self._t.get(name, []))


def test_owner_is_ok():
    c = _FakeClient(scripts=[{'user_id': 'u1'}])
    assert script_access(c, 's1', 'u1') == 'ok'


def test_member_is_ok():
    c = _FakeClient(scripts=[{'user_id': 'owner'}], members=[{'id': 'm1'}])
    assert script_access(c, 's1', 'u2') == 'ok'


def test_stranger_is_forbidden():
    c = _FakeClient(scripts=[{'user_id': 'owner'}], members=[])
    assert script_access(c, 's1', 'u2') == 'forbidden'


def test_missing_script_is_not_found():
    c = _FakeClient(scripts=[])
    assert script_access(c, 's1', 'u1') == 'not_found'


def test_report_script_id_found():
    c = _FakeClient(reports=[{'script_id': 's9'}])
    assert report_script_id(c, 'r1') == 's9'


def test_report_script_id_missing():
    c = _FakeClient(reports=[])
    assert report_script_id(c, 'r1') is None
