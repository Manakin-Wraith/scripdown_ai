import middleware.authorization as authz
from middleware.authorization import get_script_role, SCRIPT_NOT_FOUND, ROLE_RANK, from_scene, from_day, from_note


def _patch_client(monkeypatch, fake):
    monkeypatch.setattr(authz, "get_supabase_client", lambda: fake)


def test_owner_role(monkeypatch, fake_supabase):
    fake_supabase.set_table("scripts", [{"id": "s1", "user_id": "u1"}])
    _patch_client(monkeypatch, fake_supabase)
    assert get_script_role("s1", "u1") == "owner"


def test_member_role(monkeypatch, fake_supabase):
    fake_supabase.set_table("scripts", [{"id": "s1", "user_id": "owner"}])
    fake_supabase.set_table("script_members",
                            [{"script_id": "s1", "user_id": "u2", "role": "member"}])
    _patch_client(monkeypatch, fake_supabase)
    assert get_script_role("s1", "u2") == "member"


def test_non_member_returns_none(monkeypatch, fake_supabase):
    fake_supabase.set_table("scripts", [{"id": "s1", "user_id": "owner"}])
    _patch_client(monkeypatch, fake_supabase)
    assert get_script_role("s1", "stranger") is None


def test_missing_script_returns_sentinel(monkeypatch, fake_supabase):
    _patch_client(monkeypatch, fake_supabase)
    assert get_script_role("nope", "u1") is SCRIPT_NOT_FOUND


def test_role_rank_order():
    assert ROLE_RANK["viewer"] < ROLE_RANK["member"] < ROLE_RANK["admin"] < ROLE_RANK["owner"]


def test_from_scene_resolves_script(monkeypatch, fake_supabase):
    fake_supabase.set_table("scenes", [{"id": "sc1", "script_id": "s1"}])
    _patch_client(monkeypatch, fake_supabase)
    assert from_scene({"scene_id": "sc1"}) == "s1"


def test_from_scene_missing_returns_none(monkeypatch, fake_supabase):
    _patch_client(monkeypatch, fake_supabase)
    assert from_scene({"scene_id": "ghost"}) is None


def test_from_day_two_hop(monkeypatch, fake_supabase):
    fake_supabase.set_table("shooting_days", [{"id": "d1", "schedule_id": "sch1"}])
    fake_supabase.set_table("shooting_schedules", [{"id": "sch1", "script_id": "s1"}])
    _patch_client(monkeypatch, fake_supabase)
    assert from_day({"day_id": "d1"}) == "s1"


def test_from_note_resolves(monkeypatch, fake_supabase):
    fake_supabase.set_table("department_notes", [{"id": "n1", "script_id": "s9"}])
    _patch_client(monkeypatch, fake_supabase)
    assert from_note({"note_id": "n1"}) == "s9"
