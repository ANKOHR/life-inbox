"""Synthetic, fixed fixture construction. No randomness or seed required."""
from .core import KINDS, STATUSES

# Independently hand-computed: 50 per kind, 50 per status. Blocks rotate
# status each group of four; only task positions 1,5,9,... have due dates.
# Even blocks have past due dates: blocks divisible by four contain 13 active overdue tasks.
EXPECTED = {
    "total": 200,
    "by_kind": {"idea": 50, "task": 50, "message": 50, "file": 50},
    "by_status": {"inbox": 50, "active": 50, "done": 50, "archived": 50},
    "overdue_tasks": 13,
}
EXPECTED_OVERDUE = [f"item-{i:03}" for i in (1, 17, 33, 49, 65, 81, 97, 113, 129, 145, 161, 177, 193)]


def records():
    output = []
    for i in range(200):
        block = i // 4
        kind = KINDS[i % 4]
        r = {"id": f"item-{i:03}", "kind": kind,
             "title": f"Synthetic {kind} {i:03}", "body": "SYNTHETIC fixture, not Henry's data.",
             "status": STATUSES[(block + i % 4) % 4],
             "created": "2026-09-01", "synthetic": True}
        if kind == "task":
            r["due"] = "2026-09-20" if block % 2 == 0 else "2026-10-10"
        if kind == "file":
            r["path"] = f"C:\\Synthetic\\file-{i:03}.txt"
        output.append(r)
    return output


def expectations():
    return {"synthetic": True, "label": "SYNTHETIC hand-computed expectations, never input records",
            "as_of": "2026-09-30", "counts": EXPECTED, "overdue_task_ids": EXPECTED_OVERDUE}
