"""Central source of truth for the Gemini model used by AI analysis.

Set GEMINI_MODEL in the environment to switch models without a code change
(e.g. when Google retires a model). Read at call time so a value loaded via
dotenv after import is still honored.
"""
import os

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def get_gemini_model_name() -> str:
    """The Gemini model id for analysis, from GEMINI_MODEL or the default."""
    return os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
