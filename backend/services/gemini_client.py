"""Resilient single entry point for Gemini generate_content calls.

Centralizes model construction, transient-error retry with backoff, and error
classification into user-friendly messages. Every analysis code path calls
generate_with_retry() instead of talking to google.generativeai directly, so
retries, the model id, and error copy live in exactly one place.
"""
import time
import google.generativeai as genai

from utils.gemini_config import get_gemini_model_name

# User-facing copy per category. No standalone "AI" (product copy rule).
_MESSAGES = {
    "timeout": "The analysis service timed out — this is usually temporary. Click Re-analyze to try again.",
    "rate_limit": "The analysis service is busy right now. Wait a moment and Re-analyze.",
    "server": "The analysis service had a temporary error. Click Re-analyze to try again.",
    "model_unavailable": "The analysis engine was updated. Click Re-analyze to continue.",
    "bad_response": "Analysis returned an unreadable result for this scene. Click Re-analyze.",
    "unknown": "Analysis couldn't complete for this scene. Click Re-analyze to try again.",
}

# Total attempt budget per category (includes the first attempt).
_ATTEMPTS = {
    "timeout": 3,
    "rate_limit": 3,
    "server": 3,
    "model_unavailable": 2,
    "bad_response": 1,
    "unknown": 1,
}

# Base backoff seconds per category (grows as base * 2**(attempt-1)).
_BACKOFF_BASE = {"timeout": 1, "server": 1, "model_unavailable": 1, "rate_limit": 6}

_RETRYABLE = {"timeout", "rate_limit", "server", "model_unavailable"}


class GeminiError(Exception):
    """Terminal Gemini failure (retries exhausted or non-retryable).

    Carries a machine-readable category and a user-facing message.
    """

    def __init__(self, category, user_message=None, raw=None):
        self.category = category
        self.user_message = user_message or _MESSAGES.get(category, _MESSAGES["unknown"])
        self.raw = raw
        super().__init__(self.user_message)


def classify_exception(exc):
    """Map a raised exception to a category string."""
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if "deadlineexceeded" in name or "504" in msg or "timed out" in msg or "timeout" in msg:
        return "timeout"
    if "resourceexhausted" in name or "429" in msg or "quota" in msg or "rate" in msg:
        return "rate_limit"
    if "notfound" in name or "no longer available" in msg or "404" in msg:
        return "model_unavailable"
    if "serviceunavailable" in name or "internalservererror" in name \
            or any(code in msg for code in ("500", "502", "503")):
        return "server"
    return "unknown"


def generate_with_retry(prompt, *, generation_config=None, max_attempts=3, _sleep=time.sleep):
    """Call Gemini with retry/backoff on transient errors.

    Builds the model from get_gemini_model_name() each attempt (so an env/model
    change is honored). Returns response.text on success. Raises GeminiError on
    terminal failure. `_sleep` is injectable for tests.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            model = genai.GenerativeModel(get_gemini_model_name())
            response = model.generate_content(prompt, generation_config=generation_config)
            text = getattr(response, "text", None)
            if not text or not text.strip():
                raise GeminiError("bad_response")
            return text
        except GeminiError:
            raise  # already classified (e.g. empty response) — never retried here
        except Exception as exc:  # noqa: BLE001 — classify everything from the SDK
            category = classify_exception(exc)
            budget = min(max_attempts, _ATTEMPTS.get(category, 1))
            if category in _RETRYABLE and attempt < budget:
                _sleep(_BACKOFF_BASE[category] * (2 ** (attempt - 1)))
                continue
            raise GeminiError(category, raw=exc)
