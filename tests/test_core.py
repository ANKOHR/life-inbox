import pytest
from life_inbox.core import InboxError, workflow
from life_inbox.fixtures import records


def test_empty_input_renders_without_traceback():
    from life_inbox.report import render
    r = workflow([])
    assert r["counts"]["total"] == 0
    assert "Total records: 0" in render(r)


@pytest.mark.parametrize("change", [
    {"amount": -1}, {"created": "2027-01-01"}, {"title": "x" * 100001},
    {"synthetic": 1}, {"kind": "unknown"}, {"status": "unknown"},
    {"created": "2026-02-30"}, {"due": "bad"}, {"title": ""},
    {"title": "bad\u2014dash"}, {"id": []}, {"path": "wrong-kind"},
])
def test_rejects_adversarial_values(change):
    r = records()[0]
    r.update(change)
    with pytest.raises(InboxError, match="SchemaError"):
        workflow([r])


def test_duplicate_ids_rejected():
    with pytest.raises(InboxError, match="duplicate id"):
        workflow([records()[0], records()[0]])


def test_handles_unicode_and_long_inputs():
    r = records()[3]
    r["title"] = "日本語 café 😀 " + "a" * 50000
    r["path"] = r"C:\Users\Henry\資料\my file.txt"
    result = workflow([r])
    assert result["records"][0] == r


def test_overdue_boundaries():
    task = records()[1]
    task["due"] = "2026-09-30"
    assert workflow([task])["overdue_task_ids"] == []
    task["due"] = "2026-09-29"
    assert workflow([task])["overdue_task_ids"] == [task["id"]]
    for status in ("done", "archived"):
        task["status"] = status
        assert workflow([task])["overdue_task_ids"] == []
    task.pop("due")
    assert workflow([task])["overdue_task_ids"] == []


def test_future_due_is_valid():
    task = records()[1]
    task["due"] = "2099-01-01"
    assert workflow([task])["counts"]["overdue_tasks"] == 0


def test_five_handwritten_records():
    values = [
        {"id": "a", "kind": "idea", "title": "Build a planner", "status": "inbox", "created": "2026-09-01", "synthetic": True},
        {"id": "b", "kind": "task", "title": "Send application", "status": "active", "created": "2026-09-01", "due": "2026-09-20", "synthetic": True},
        {"id": "c", "kind": "message", "title": "Reply to teacher", "status": "inbox", "created": "2026-09-01", "synthetic": True},
        {"id": "d", "kind": "file", "title": "CV", "path": "CV.pdf", "status": "archived", "created": "2026-09-01", "synthetic": True},
        {"id": "e", "kind": "task", "title": "Finished homework", "status": "done", "created": "2026-09-01", "due": "2026-09-02", "synthetic": True},
    ]
    r = workflow(values)
    assert r["counts"] == {"total": 5, "by_kind": {"idea": 1, "task": 2, "message": 1, "file": 1}, "by_status": {"inbox": 2, "active": 1, "done": 1, "archived": 1}, "overdue_tasks": 1}
    assert r["overdue_task_ids"] == ["b"]
