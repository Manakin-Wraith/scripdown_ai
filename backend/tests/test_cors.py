"""CORS allowlist: production + local dev + this team's Vercel previews only."""
import pytest

import app as app_module


@pytest.fixture
def client():
    return app_module.app.test_client()


def _acao(client, origin):
    r = client.options(
        "/health",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    return r.headers.get("Access-Control-Allow-Origin")


@pytest.mark.parametrize("origin", [
    "https://app.slateone.studio",
    "http://localhost:5173",
    "https://frontend-3cuarud79-manakin-wraiths-projects.vercel.app",
    "https://frontend-git-perf-page-load-audit-manakin-wraiths-projects.vercel.app",
])
def test_allowed_origins(client, origin):
    assert _acao(client, origin) == origin


@pytest.mark.parametrize("origin", [
    "https://frontend-abc-someone-elses-projects.vercel.app",
    "https://frontend-abc-manakin-wraiths-projects.vercel.app.evil.com",
    "https://evil.com/frontend-abc-manakin-wraiths-projects.vercel.app",
    "http://frontend-abc-manakin-wraiths-projects.vercel.app",
])
def test_rejected_origins(client, origin):
    assert _acao(client, origin) is None
