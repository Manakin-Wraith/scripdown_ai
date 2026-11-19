"""CORS allowlist: production + local dev + exact origins from CORS_EXTRA_ORIGINS only."""
import importlib

import pytest

PREVIEW = "https://frontend-3cuarud79-manakin-wraiths-projects.vercel.app"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("CORS_EXTRA_ORIGINS", f" {PREVIEW} , ")
    import app as app_module
    app_module = importlib.reload(app_module)
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
    PREVIEW,
])
def test_allowed_origins(client, origin):
    assert _acao(client, origin) == origin


@pytest.mark.parametrize("origin", [
    # lookalike an outside Vercel account could produce (scope "wraiths", project "frontend-x-manakin")
    "https://frontend-x-manakin-wraiths-projects.vercel.app",
    "https://frontend-other111-manakin-wraiths-projects.vercel.app",
    PREVIEW + ".evil.com",
    "http://frontend-3cuarud79-manakin-wraiths-projects.vercel.app",
])
def test_rejected_origins(client, origin):
    assert _acao(client, origin) is None
