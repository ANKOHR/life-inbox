import json
import subprocess
import sys
import time
from pathlib import Path
import pytest
from life_inbox.cli import main, load_input, atomic_write
from life_inbox.core import InboxError


def invoke(tmp_path, *args):
    return main(["--state", str(tmp_path / "state.json"), *args])


def test_run_completes_on_fixture(tmp_path, capsys):
    start = time.perf_counter()
    directory = tmp_path / "input"
    assert invoke(tmp_path, "fixtures", "--out", str(directory)) == 0
    assert invoke(tmp_path, "run", "--input", str(directory)) == 0
    assert invoke(tmp_path, "report", "--format", "md") == 0
    assert time.perf_counter() - start < 5
    assert "Data provenance: 200 synthetic" in capsys.readouterr().out


def test_determinism_byte_identical(tmp_path):
    directory = tmp_path / "input"
    invoke(tmp_path, "fixtures", "--out", str(directory))
    first = {}
    for i in range(2):
        invoke(tmp_path, "run", "--input", str(directory))
        for fmt in ("md", "json"):
            p = tmp_path / ("report." + fmt)
            invoke(tmp_path, "report", "--format", fmt, "--out", str(p))
            if i == 0:
                first[fmt] = p.read_bytes()
            else:
                assert p.read_bytes() == first[fmt]
        if i == 0:
            state = (tmp_path / "state.json").read_bytes()
        else:
            assert (tmp_path / "state.json").read_bytes() == state


@pytest.mark.parametrize("filename,content,line", [("bad.json", "[\n invalid]", 2), ("bad.jsonl", "# comment\n{bad}", 2), ("bad.csv", "bad", 1), ("bad.yaml", "bad:", 1)])
def test_malformed_input_named_error(tmp_path, capsys, filename, content, line):
    directory = tmp_path / "input"
    directory.mkdir()
    (directory / filename).write_text(content)
    assert invoke(tmp_path, "run", "--input", str(directory)) == 2
    error = capsys.readouterr().err
    assert filename in error and f"line {line}" in error
    assert "Traceback" not in error


def test_cli_smoke_all_subcommands(tmp_path, capsys):
    directory = tmp_path / "personal"
    assert invoke(tmp_path, "capture", "--input", str(directory), "--id", "one", "--kind", "task", "--title", "Apply", "--created", "2026-09-30", "--due", "2026-10-02") == 0
    assert invoke(tmp_path, "triage", "--input", str(directory), "--id", "one", "--status", "active") == 0
    assert invoke(tmp_path, "run", "--input", str(directory)) == 0
    assert invoke(tmp_path, "report", "--format", "json") == 0
    result = json.loads((tmp_path / "state.json").read_text())
    assert result["records"][0]["status"] == "active"
    assert result["provenance"]["real_records"] == 1
    for command in ("fixtures", "run", "report", "capture", "triage"):
        with pytest.raises(SystemExit) as e:
            main([command, "--help"])
        assert e.value.code == 0
    assert "Example:" in capsys.readouterr().out


def test_empty_directory_cli(tmp_path, capsys):
    p = tmp_path / "empty"
    p.mkdir()
    assert invoke(tmp_path, "run", "--input", str(p)) == 0
    assert invoke(tmp_path, "report") == 0
    assert "Total records: 0" in capsys.readouterr().out


def test_missing_input(tmp_path, capsys):
    assert invoke(tmp_path, "run", "--input", str(tmp_path / "missing")) == 2
    assert "MissingInput" in capsys.readouterr().err
    assert invoke(tmp_path, "report") == 2
    assert "run li run" in capsys.readouterr().err


def test_report_write_failure_no_partial_files(tmp_path, capsys):
    p = tmp_path / "empty"
    p.mkdir()
    invoke(tmp_path, "run", "--input", str(p))
    target = tmp_path / "destination"
    target.mkdir()
    before = set(tmp_path.iterdir())
    assert invoke(tmp_path, "report", "--out", str(target)) == 2
    assert "WriteError" in capsys.readouterr().err
    assert set(tmp_path.iterdir()) == before


def test_failed_replace_preserves_existing_and_cleans_temp(tmp_path, monkeypatch):
    p = tmp_path / "report.md"
    p.write_text("previous")
    def fail(*args):
        raise OSError("planted failure")
    monkeypatch.setattr("life_inbox.cli.os.replace", fail)
    with pytest.raises(InboxError, match="WriteError"):
        atomic_write(p, "new")
    assert p.read_text() == "previous"
    assert list(tmp_path.iterdir()) == [p]


def test_bad_input_preserves_previous_results(tmp_path):
    p = tmp_path / "input"
    p.mkdir()
    invoke(tmp_path, "run", "--input", str(p))
    before = (tmp_path / "state.json").read_bytes()
    (p / "bad.jsonl").write_text("{bad}")
    assert invoke(tmp_path, "run", "--input", str(p)) == 2
    assert (tmp_path / "state.json").read_bytes() == before


def test_capture_duplicate_preserves_source(tmp_path):
    p = tmp_path / "input"
    args = ("capture", "--input", str(p), "--id", "one", "--kind", "idea", "--title", "Idea", "--created", "2026-09-30")
    assert invoke(tmp_path, *args) == 0
    before = (p / "captures.jsonl").read_bytes()
    assert invoke(tmp_path, *args) == 2
    assert (p / "captures.jsonl").read_bytes() == before


def test_json_array_triage(tmp_path):
    from life_inbox.fixtures import records
    p = tmp_path / "input"
    p.mkdir()
    f = p / "input.json"
    f.write_text(json.dumps(records()[:1]))
    assert invoke(tmp_path, "triage", "--input", str(p), "--id", "item-000", "--status", "done") == 0
    assert json.loads(f.read_text())[0]["status"] == "done"


def test_actual_process_smoke(tmp_path):
    result = subprocess.run([sys.executable, "-m", "life_inbox.cli", "fixtures", "--out", str(tmp_path / "fixture")], capture_output=True, text=True)
    assert result.returncode == 0
    assert "SYNTHETIC" in result.stdout
    assert "Traceback" not in result.stderr


def test_unicode_process_output(tmp_path):
    from life_inbox.fixtures import records
    p = tmp_path / "input"
    p.mkdir()
    record = records()[3]
    record["title"] = "日本語 café 😀 " + "x" * 50000
    record["path"] = r"C:\Users\Henry\資料\my file.txt"
    (p / "records.json").write_text(json.dumps([record], ensure_ascii=False), encoding="utf-8")
    state = str(tmp_path / "result.json")
    for args in [("run", "--input", str(p)), ("report", "--format", "json")]:
        result = subprocess.run([sys.executable, "-m", "life_inbox.cli", "--state", state, *args], capture_output=True, encoding="utf-8")
        assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["records"][0]["title"] == record["title"]


def test_no_em_dashes_in_source_and_help(capsys):
    root = Path(__file__).resolve().parents[1]
    paths = list((root / "life_inbox").glob("*.py")) + list((root / "tests").glob("*.py")) + list(root.glob("*.md"))
    for path in paths:
        assert chr(0x2014) not in path.read_text(encoding="utf-8"), path.name
    for command in ("fixtures", "run", "report", "capture", "triage"):
        with pytest.raises(SystemExit):
            main([command, "--help"])
    assert chr(0x2014) not in capsys.readouterr().out
