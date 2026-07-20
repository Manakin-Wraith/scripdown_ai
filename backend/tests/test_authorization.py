import middleware.authorization as authz
from middleware.authorization import get_script_role, SCRIPT_NOT_FOUND, ROLE_RANK


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
