import json
from life_inbox.cli import main, load_input
from life_inbox.fixtures import records, EXPECTED, EXPECTED_OVERDUE
from life_inbox.core import workflow


def test_fixtures_labelled_synthetic(tmp_path):
    assert main(["fixtures", "--out", str(tmp_path)]) == 0
    text = (tmp_path / "records.jsonl").read_text(encoding="utf-8")
    assert text.startswith("# SYNTHETIC")
    assert len(records()) == 200
    assert all(r["synthetic"] is True for r in records())
    assert json.loads((tmp_path / "expectations.json").read_text())["synthetic"] is True
    assert "SYNTHETIC" in (tmp_path / "README.md").read_text()


def test_fixture_ground_truth_matches_hand_computed():
    r = workflow(records())
    assert r["counts"] == EXPECTED
    assert r["overdue_task_ids"] == EXPECTED_OVERDUE
    assert sum(r["counts"]["by_kind"].values()) == 200
    assert sum(r["counts"]["by_status"].values()) == 200


def test_corruption_changes_computed_report(tmp_path):
    main(["fixtures", "--out", str(tmp_path)])
    p = tmp_path / "records.jsonl"
    text = p.read_text(encoding="utf-8").replace('"due": "2026-09-20"', '"due": "2026-10-20"')
    p.write_text(text, encoding="utf-8")
    assert load_input(tmp_path, "2026-09-30")["counts"]["overdue_tasks"] == 0
    # Corrupting the expectations file cannot change computed figures.
    (tmp_path / "expectations.json").write_text('{"total": 99999}')
    assert load_input(tmp_path, "2026-09-30")["counts"]["total"] == 200
