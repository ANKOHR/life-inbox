import json
from life_inbox.core import workflow
from life_inbox.fixtures import records, EXPECTED, EXPECTED_OVERDUE
from life_inbox.report import render


def test_report_matches_ground_truth_exact():
    r = json.loads(render(workflow(records()), "json"))
    assert r["counts"] == EXPECTED
    assert r["overdue_task_ids"] == EXPECTED_OVERDUE
    assert "Total records: 200" in render(r)


def test_report_zero_false_positives():
    actual = set(workflow(records())["overdue_task_ids"])
    truth = set(EXPECTED_OVERDUE)
    assert actual - truth == set()
    assert truth - actual == set()


def test_report_carries_provenance_banner():
    values = records()[:2]
    values[0]["synthetic"] = False
    for fmt in ("md", "json"):
        report = render(workflow(values), fmt)
        assert "Data provenance: 1 synthetic fixture records; 1 author-declared real records" in report
        assert "not independently verified" in report


def test_hypothetical_figures_labelled():
    for fmt in ("md", "json"):
        report = render(workflow(records()), fmt)
        assert "Unmeasured: no baseline supplied; no savings claimed." in report
        assert "hypothetical savings: 10" not in report


def test_no_em_dashes_in_outputs():
    for fmt in ("md", "json"):
        assert "\u2014" not in render(workflow(records()), fmt)
