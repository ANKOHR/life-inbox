"""Pure validation and classification. No clocks, filesystem, or estimates."""
from datetime import date

KINDS = ("idea", "task", "message", "file")
STATUSES = ("inbox", "active", "done", "archived")
FIELDS = {"id", "kind", "title", "body", "status", "created", "due", "path", "synthetic"}
MAX_TEXT = 100_000

class InboxError(ValueError):
    """A named, user-correctable input error."""


def validate(record, as_of):
    if not isinstance(record, dict):
        raise InboxError("SchemaError: record must be an object")
    extra = set(record) - FIELDS
    if extra:
        raise InboxError("SchemaError: unknown field(s): " + ", ".join(sorted(extra)))
    for field in ("id", "kind", "title", "status", "created", "synthetic"):
        if field not in record:
            raise InboxError(f"SchemaError: missing field {field}")
    for field in ("id", "title", "body", "path"):
        if field in record:
            value = record[field]
            if not isinstance(value, str) or len(value) > MAX_TEXT or (field in ("id", "title") and not value.strip()):
                raise InboxError(f"SchemaError: {field} must be text of at most {MAX_TEXT} characters and id/title must be nonempty")
            if "\u2014" in value:
                raise InboxError(f"SchemaError: {field} contains forbidden U+2014; use a hyphen")
    if record["kind"] not in KINDS:
        raise InboxError("SchemaError: kind must be idea, task, message, or file")
    if record["status"] not in STATUSES:
        raise InboxError("SchemaError: status must be inbox, active, done, or archived")
    if type(record["synthetic"]) is not bool:
        raise InboxError("SchemaError: synthetic must be a boolean")
    for field in ("created", "due"):
        if field in record:
            value = record[field]
            try:
                if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
                    raise ValueError()
            except (ValueError, TypeError):
                raise InboxError(f"SchemaError: {field} must be YYYY-MM-DD") from None
    if record["created"] > as_of:
        raise InboxError("SchemaError: created is after as_of")
    if "due" in record and record["kind"] != "task":
        raise InboxError("SchemaError: due is only allowed on tasks")
    if record["kind"] == "file" and not record.get("path"):
        raise InboxError("SchemaError: file requires path")
    if "path" in record and record["kind"] != "file":
        raise InboxError("SchemaError: path is only allowed on files")
    return dict(record)


def workflow(records, as_of="2026-09-30"):
    try:
        if date.fromisoformat(as_of).isoformat() != as_of:
            raise ValueError()
    except (ValueError, TypeError):
        raise InboxError("SchemaError: as_of must be YYYY-MM-DD") from None
    checked, ids = [], set()
    for raw in records:
        item = validate(raw, as_of)
        if item["id"] in ids:
            raise InboxError(f"SchemaError: duplicate id {item['id']!r}")
        ids.add(item["id"])
        checked.append(item)
    checked.sort(key=lambda r: r["id"])
    overdue = [r["id"] for r in checked if r["kind"] == "task" and r["status"] in ("inbox", "active") and r.get("due", as_of) < as_of]
    return {
        "schema_version": 1, "as_of": as_of,
        "provenance": {"synthetic_records": sum(r["synthetic"] for r in checked),
                       "real_records": sum(not r["synthetic"] for r in checked),
                       "note": "Real means input declared synthetic:false by its author; ownership is not independently verified."},
        "counts": {"total": len(checked),
                   "by_kind": {k: sum(r["kind"] == k for r in checked) for k in KINDS},
                   "by_status": {s: sum(r["status"] == s for r in checked) for s in STATUSES},
                   "overdue_tasks": len(overdue)},
        "overdue_task_ids": overdue,
        "inbox_ids": [r["id"] for r in checked if r["status"] == "inbox"],
        "records": checked,
        "honesty": {"time_saved": "Unmeasured: no baseline supplied; no savings claimed.",
                    "money_saved": "Unmeasured: no baseline supplied; no savings claimed."},
    }
