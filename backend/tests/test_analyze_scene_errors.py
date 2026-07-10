"""analyze_scene_with_gemini must raise GeminiError instead of swallowing."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import routes.supabase_routes as sr
from services.gemini_client import GeminiError


@pytest.fixture(autouse=True)
def _key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")


def test_analyzer_raises_on_gemini_error(monkeypatch):
    def boom(*_a, **_k):
        raise GeminiError("timeout")
    monkeypatch.setattr(sr, "generate_with_retry", boom)
    with pytest.raises(GeminiError) as ei:
        sr.analyze_scene_with_gemini("INT. ROOM - DAY\nAction.", "INT. ROOM - DAY")
    assert ei.value.category == "timeout"


def test_analyzer_raises_bad_response_on_unparseable_json(monkeypatch):
    monkeypatch.setattr(sr, "generate_with_retry", lambda *_a, **_k: "not json at all")
    with pytest.raises(GeminiError) as ei:
        sr.analyze_scene_with_gemini("INT. ROOM - DAY\nAction.", "INT. ROOM - DAY")
    assert ei.value.category == "bad_response"


def test_analyzer_success_returns_dict(monkeypatch):
    monkeypatch.setattr(
        sr, "generate_with_retry",
        lambda *_a, **_k: '{"characters":["BOB"],"props":[],"description":"x"}',
    )
    out = sr.analyze_scene_with_gemini("INT. ROOM - DAY\nBOB enters.", "INT. ROOM - DAY")
    assert out["characters"] == ["BOB"]
    assert out["description"] == "x"
