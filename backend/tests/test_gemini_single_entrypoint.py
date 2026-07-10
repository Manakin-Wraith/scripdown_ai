"""Every Gemini generate_content call must go through gemini_client.

Enforces the single-entrypoint invariant: only services/gemini_client.py may
call .generate_content( directly; all other call sites use generate_with_retry
so retry + error classification is never bypassed.
"""
import os
import re
import glob

BACKEND = os.path.join(os.path.dirname(__file__), "..")
_CALL_RE = re.compile(r"\.generate_content\s*\(")
_ALLOWED = {os.path.normpath(os.path.join(BACKEND, "services", "gemini_client.py"))}


def _source_files():
    for sub in ("routes", "services"):
        yield from glob.glob(os.path.join(BACKEND, sub, "*.py"))


def test_only_client_calls_generate_content():
    offenders = []
    for path in _source_files():
        if os.path.normpath(path) in _ALLOWED:
            continue
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                if _CALL_RE.search(line):
                    offenders.append(f"{os.path.relpath(path, BACKEND)}:{lineno}")
    assert not offenders, (
        "generate_content called outside gemini_client — route through "
        "generate_with_retry instead:\n" + "\n".join(offenders)
    )
