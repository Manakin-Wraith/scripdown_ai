"""Pure CSV parser for per-production crew import. No DB access."""
import csv
import io

RECOGNIZED_HEADERS = {"name", "email", "phone", "company_name", "role",
                      "department", "rate", "rate_unit", "notes"}
_VALID_RATE_UNITS = {"day", "week", "flat"}


def _norm_header(h):
    return (h or "").strip().lower().replace(" ", "_")


def parse_crew_csv(text, valid_codes, name_to_code):
    reader = csv.reader(io.StringIO(text))
    try:
        raw_header = next(reader)
    except StopIteration:
        return {"rows": [], "errors": [], "fatal": "empty file"}

    headers = [_norm_header(h) for h in raw_header]
    if "name" not in headers:
        return {"rows": [], "errors": [], "fatal": "CSV must have a 'name' column"}

    code_by_name = {v.lower(): k for k, v in (name_to_code or {}).items()}
    rows, errors = [], []

    for offset, raw in enumerate(reader):
        line = offset + 2  # header is line 1
        cell = {headers[i]: (raw[i].strip() if i < len(raw) else "")
                for i in range(len(headers))}

        name = cell.get("name", "").strip()
        if not name:
            errors.append({"line": line, "reason": "missing name"})
            continue

        dept_code = None
        dept_raw = cell.get("department", "").strip()
        if dept_raw:
            if dept_raw in valid_codes:
                dept_code = dept_raw
            elif dept_raw.lower() in code_by_name:
                dept_code = code_by_name[dept_raw.lower()]
            else:
                errors.append({"line": line, "reason": f"unknown department '{dept_raw}'"})
                continue

        rate = None
        rate_raw = cell.get("rate", "").strip()
        if rate_raw:
            try:
                rate = float(rate_raw)
            except ValueError:
                errors.append({"line": line, "reason": f"rate '{rate_raw}' is not a number"})
                continue

        rate_unit = cell.get("rate_unit", "").strip().lower() or None
        if rate_unit and rate_unit not in _VALID_RATE_UNITS:
            errors.append({"line": line, "reason": f"rate_unit '{rate_unit}' ignored (use day/week/flat)"})
            rate_unit = None

        rows.append({
            "name": name,
            "email": cell.get("email") or None,
            "phone": cell.get("phone") or None,
            "company_name": cell.get("company_name") or None,
            "role": cell.get("role") or None,
            "department_code": dept_code,
            "rate": rate,
            "rate_unit": rate_unit,
            "notes": cell.get("notes") or None,
        })

    return {"rows": rows, "errors": errors, "fatal": None}
