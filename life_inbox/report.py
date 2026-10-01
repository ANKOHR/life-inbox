"""Stable, honest rendering of computed results."""
import json


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def banner(result):
    p = result["provenance"]
    return (f"Data provenance: {p['synthetic_records']} synthetic fixture records; "
            f"{p['real_records']} author-declared real records. {p['note']}")


def render(result, format="md"):
    if format == "json":
        return json_text({"banner": banner(result), **result})
    if format != "md":
        raise ValueError("Unsupported report format")
    c = result["counts"]
    lines = ["# Life Inbox", "", banner(result), "", f"As of: {result['as_of']}", "",
             f"Total records: {c['total']}", f"Overdue open tasks: {c['overdue_tasks']}", "",
             "## Counts", "", "| Kind | Count |", "| --- | --- |"]
    lines += [f"| {k} | {v} |" for k, v in c["by_kind"].items()]
    lines += ["", "| Status | Count |", "| --- | --- |"]
    lines += [f"| {k} | {v} |" for k, v in c["by_status"].items()]
    lines += ["", "## Traceability", "", "Every record below includes its source file and line when loaded through the CLI.", "", "```json", json_text(result["records"]).rstrip(), "```", "",
              "Overdue task IDs: " + json.dumps(result["overdue_task_ids"], ensure_ascii=False),
              "Inbox IDs: " + json.dumps(result["inbox_ids"], ensure_ascii=False), "", "## Honesty", "",
              result["honesty"]["time_saved"], result["honesty"]["money_saved"], ""]
    return "\n".join(lines)
