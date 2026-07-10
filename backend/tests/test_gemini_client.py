"""Unit tests for the resilient Gemini client. No live API calls."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import gemini_client as gc
from services.gemini_client import GeminiError, classify_exception, generate_with_retry


class FakeResp:
    def __init__(self, text):
        self.text = text


def _fake_model_factory(behaviors):
    """behaviors: list of callables; each call to generate_content pops the next.
    A callable returns a FakeResp or raises."""
    calls = {"n": 0}

    class FakeModel:
        def __init__(self, *_a, **_k):
            pass

        def generate_content(self, *_a, **_k):
            i = calls["n"]
            calls["n"] += 1
            return behaviors[i]()

    return FakeModel, calls


def test_success_returns_text(monkeypatch):
    FakeModel, calls = _fake_model_factory([lambda: FakeResp("hello")])
    monkeypatch.setattr(gc.genai, "GenerativeModel", FakeModel)
    out = generate_with_retry("p", _sleep=lambda _s: None)
    assert out == "hello"
    assert calls["n"] == 1


def test_timeout_retries_then_raises(monkeypatch):
    def boom():
        raise Exception("504 The request timed out")
    FakeModel, calls = _fake_model_factory([boom, boom, boom])
    monkeypatch.setattr(gc.genai, "GenerativeModel", FakeModel)
    with pytest.raises(GeminiError) as ei:
        generate_with_retry("p", _sleep=lambda _s: None)
    assert ei.value.category == "timeout"
    assert calls["n"] == 3  # 3 attempts


def test_timeout_recovers_on_retry(monkeypatch):
    def boom():
        raise Exception("504 timed out")
    FakeModel, calls = _fake_model_factory([boom, lambda: FakeResp("ok")])
    monkeypatch.setattr(gc.genai, "GenerativeModel", FakeModel)
    assert generate_with_retry("p", _sleep=lambda _s: None) == "ok"
    assert calls["n"] == 2


def test_model_unavailable_retries_once(monkeypatch):
    def boom():
        raise Exception("404 This model models/x is no longer available")
    FakeModel, calls = _fake_model_factory([boom, boom, boom])
    monkeypatch.setattr(gc.genai, "GenerativeModel", FakeModel)
    with pytest.raises(GeminiError) as ei:
        generate_with_retry("p", _sleep=lambda _s: None)
    assert ei.value.category == "model_unavailable"
    assert calls["n"] == 2  # budget of 2 for model_unavailable


def test_empty_text_is_bad_response_no_retry(monkeypatch):
    FakeModel, calls = _fake_model_factory([lambda: FakeResp("   ")])
    monkeypatch.setattr(gc.genai, "GenerativeModel", FakeModel)
    with pytest.raises(GeminiError) as ei:
        generate_with_retry("p", _sleep=lambda _s: None)
    assert ei.value.category == "bad_response"
    assert calls["n"] == 1


def test_classify_exception_shapes():
    assert classify_exception(Exception("504 timed out")) == "timeout"
    assert classify_exception(Exception("429 quota exceeded")) == "rate_limit"
    assert classify_exception(Exception("model no longer available")) == "model_unavailable"
    assert classify_exception(Exception("503 service unavailable")) == "server"
    assert classify_exception(Exception("weird boom")) == "unknown"


def test_classify_does_not_confuse_generate_with_rate():
    assert classify_exception(Exception("Failed to generate content: bad arg")) == "unknown"
    assert classify_exception(Exception("429 rate limit exceeded")) == "rate_limit"
    # digits embedded in a larger number must not falsely match bare "404"/"500" substrings
    assert classify_exception(Exception("processed 15404 items, batch 25500")) == "unknown"
    # a genuinely standalone 404 token still classifies as model_unavailable
    assert classify_exception(Exception("scene had error code 404")) == "model_unavailable"


def test_messages_never_say_ai():
    for cat in ("timeout", "rate_limit", "server", "model_unavailable", "bad_response", "unknown"):
        assert "ai" not in GeminiError(cat).user_message.lower().split()  # no standalone "AI"
