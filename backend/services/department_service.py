"""Shared access to the `departments` reference list.

Moved here from routes/invite_routes.py so route modules don't import each
other. Same cache behaviour as before: one read, memoised for the process.
"""
import logging
from db.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)

_cache = None


def _reset_departments_cache():
    """Test helper — clear the process-level cache."""
    global _cache
    _cache = None


def get_departments_list():
    """Return [{code, name, color}, ...] ordered by sort_order; [] on failure."""
    global _cache
    if _cache is None:
        try:
            res = (get_supabase_admin().table("departments")
                   .select("code, name, color").order("sort_order").execute())
            _cache = res.data or []
        except Exception as e:  # noqa: BLE001 — reference data, degrade gracefully
            logger.error("Failed to fetch departments: %s", e)
            _cache = []
    return _cache


def get_department_name(code):
    for d in get_departments_list():
        if d["code"] == code:
            return d["name"]
    return code


def valid_department_codes():
    return {d["code"] for d in get_departments_list()}
