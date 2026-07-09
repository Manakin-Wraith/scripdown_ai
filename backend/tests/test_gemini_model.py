"""Regression guard: no source file may instantiate a retired Gemini model.

Google removed `gemini-2.0-flash` (generateContent returns 404
"This model ... is no longer available"). Any GenerativeModel() pinned to a
retired id breaks analysis in production. This test scans the backend source
so a stale model id can't be reintroduced at any call site.
"""
import os
import re
import glob

BACKEND = os.path.join(os.path.dirname(__file__), "..")

# Exact model ids known to be retired for generateContent.
RETIRED_MODEL_IDS = ["gemini-2.0-flash"]

# GenerativeModel('<id>') / GenerativeModel("<id>")
_MODEL_CALL_RE = re.compile(r"""GenerativeModel\(\s*['"]([^'"]+)['"]""")


def _source_files():
    for sub in ("routes", "services"):
        yield from glob.glob(os.path.join(BACKEND, sub, "*.py"))


def test_no_retired_gemini_model_instantiated():
    offenders = []
    for path in _source_files():
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                for model_id in _MODEL_CALL_RE.findall(line):
                    if model_id in RETIRED_MODEL_IDS:
                        offenders.append(f"{os.path.relpath(path, BACKEND)}:{lineno} -> {model_id}")
    assert not offenders, "Retired Gemini model still instantiated:\n" + "\n".join(offenders)


def test_gemini_model_name_default(monkeypatch):
    from utils.gemini_config import get_gemini_model_name, DEFAULT_GEMINI_MODEL
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    assert get_gemini_model_name() == DEFAULT_GEMINI_MODEL
    assert DEFAULT_GEMINI_MODEL not in RETIRED_MODEL_IDS


def test_gemini_model_name_env_override(monkeypatch):
    from utils.gemini_config import get_gemini_model_name
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash")
    assert get_gemini_model_name() == "gemini-3.5-flash"


def test_gemini_model_name_blank_env_falls_back(monkeypatch):
    from utils.gemini_config import get_gemini_model_name, DEFAULT_GEMINI_MODEL
    monkeypatch.setenv("GEMINI_MODEL", "")
    assert get_gemini_model_name() == DEFAULT_GEMINI_MODEL
