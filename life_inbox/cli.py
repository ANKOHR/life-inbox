"""Local filesystem adapter and CLI. No network services."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from .core import InboxError, workflow, KINDS, STATUSES
from .fixtures import records, expectations
from .report import json_text, render


def atomic_write(path, text):
    path = Path(path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as f:
            temporary = Path(f.name)
            f.write(text)
        os.replace(temporary, path)
    except OSError as e:
        raise InboxError(f"WriteError: {path}: {e.strerror or str(e)}") from None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def load_input(directory, as_of):
    directory = Path(directory)
    if not directory.is_dir():
        raise InboxError(f"MissingInput: {directory}; use li fixtures --out <dir> or create an input directory")
    items, sources, seen = [], {}, set()
    for path in sorted(directory.iterdir()):
        if path.name in ("expectations.json", "README.md") or path.is_dir():
            continue
        if path.suffix.lower() not in (".json", ".jsonl"):
            raise InboxError(f"SchemaError: {path}: line 1: unsupported input format; use JSON or JSONL")
        try:
            content = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as e:
            raise InboxError(f"ReadError: {path}: line 1: {e}") from None
        entries = []
        if path.suffix.lower() == ".jsonl":
            for line, text in enumerate(content.splitlines(), 1):
                if not text.strip() or text.lstrip().startswith("#"):
                    continue
                try:
                    entries.append((line, json.loads(text)))
                except json.JSONDecodeError as e:
                    raise InboxError(f"ParseError: {path}: line {line}: {e.msg}") from None
        else:
            try:
                value = json.loads(content)
            except json.JSONDecodeError as e:
                raise InboxError(f"ParseError: {path}: line {e.lineno}: {e.msg}") from None
            if not isinstance(value, list):
                raise InboxError(f"SchemaError: {path}: line 1: JSON input must be an array of records")
            # JSON array schema errors identify the document start; JSONL gives exact record lines.
            entries = [(1, r) for r in value]
        for line, raw in entries:
            try:
                valid = workflow([raw], as_of)["records"][0]
                if valid["id"] in seen:
                    raise InboxError(f"SchemaError: duplicate id {valid['id']!r}")
                seen.add(valid["id"])
            except InboxError as e:
                raise InboxError(f"{e}: {path}: line {line}") from None
            items.append(valid)
            sources[valid["id"]] = {"file": path.name, "line": line}
    result = workflow(items, as_of)
    for r in result["records"]:
        r["source"] = sources[r["id"]]
    return result


def parser():
    p = argparse.ArgumentParser(description="Capture and triage ideas, tasks, messages and file references locally.")
    p.add_argument("--state", default=".life-inbox/results.json", help="Result file, default .life-inbox/results.json")
    sub = p.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fixtures", help="Generate 200 labelled synthetic records", epilog="Example: li fixtures --out demo")
    f.add_argument("--out", required=True)
    r = sub.add_parser("run", help="Validate inputs and compute the inbox", epilog="Example: li run --input demo --as-of 2026-09-30")
    r.add_argument("--input", required=True)
    r.add_argument("--as-of", default="2026-09-30", help="Explicit reference date; fixed default 2026-09-30, never today's clock")
    r = sub.add_parser("report", help="Render computed results with provenance", epilog="Example: li report --format md --out report.md")
    r.add_argument("--format", choices=("md", "json"), default="md")
    r.add_argument("--out", help="Optional atomic report destination")
    c = sub.add_parser("capture", help="Add an author-entered record to a JSONL inbox", epilog='Example: li capture --input personal --id task-1 --kind task --title "Submit application" --created 2026-09-30 --due 2026-10-02')
    c.add_argument("--input", required=True)
    for field in ("id", "title", "created"):
        c.add_argument("--" + field, required=True)
    c.add_argument("--kind", required=True, choices=KINDS)
    c.add_argument("--status", default="inbox", choices=STATUSES)
    for field in ("body", "due", "path"):
        c.add_argument("--" + field)
    c.add_argument("--synthetic", action="store_true", help="Explicitly label illustrative or synthetic captures")
    c.add_argument("--as-of", default="2026-09-30")
    t = sub.add_parser("triage", help="Change a record's status in source input", epilog="Example: li triage --input personal --id task-1 --status active")
    t.add_argument("--input", required=True)
    t.add_argument("--id", required=True)
    t.add_argument("--status", required=True, choices=STATUSES)
    t.add_argument("--as-of", default="2026-09-30")
    return p


def read_state(path):
    try:
        result = json.loads(Path(path).read_text(encoding="utf-8"))
        original = result["records"]
        clean = [{k: v for k, v in r.items() if k != "source"} for r in original]
        checked = workflow(clean, result["as_of"])
        checked["records"] = original
        return checked
    except FileNotFoundError:
        raise InboxError(f"MissingInput: {path}; run li run --input <dir> first") from None
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise InboxError(f"StateError: {path}: invalid results; rerun li run ({e})") from None


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        if args.command == "fixtures":
            directory = Path(args.out)
            if directory.exists() and any(directory.iterdir()):
                raise InboxError(f"WriteError: {directory}: fixtures destination must be empty")
            atomic_write(directory / "records.jsonl", "# SYNTHETIC fixture records, no real personal data\n" + "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records()))
            atomic_write(directory / "expectations.json", json_text(expectations()))
            atomic_write(directory / "README.md", "<!-- SYNTHETIC fixture -->\n# Synthetic fixture\n200 synthetic records. See expectations.json for independent hand-computed ground truth.\n")
            print("Generated 200 SYNTHETIC records; fixed construction, no random seed.")
        elif args.command == "run":
            result = load_input(args.input, args.as_of)
            atomic_write(args.state, json_text(result))
            print(f"Computed {result['counts']['total']} records. Synthetic: {result['provenance']['synthetic_records']}; author-declared real: {result['provenance']['real_records']}. Savings unmeasured.")
        elif args.command == "report":
            text = render(read_state(args.state), args.format)
            if args.out:
                atomic_write(args.out, text)
            else:
                sys.stdout.write(text)
        elif args.command == "capture":
            directory = Path(args.input)
            existing = load_input(directory, args.as_of) if directory.exists() else workflow([], args.as_of)
            record = {k: getattr(args, k) for k in ("id", "kind", "title", "status", "created", "synthetic")}
            record.update({k: getattr(args, k) for k in ("body", "due", "path") if getattr(args, k) is not None})
            workflow([{k: v for k, v in r.items() if k != "source"} for r in existing["records"]] + [record], args.as_of)
            target = directory / "captures.jsonl"
            old = target.read_text(encoding="utf-8") if target.exists() else ""
            label = "# SYNTHETIC capture\n" if args.synthetic else ""
            atomic_write(target, old + ("\n" if old and not old.endswith("\n") else "") + label + json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            print(f"Captured {record['id']}: {'synthetic' if args.synthetic else 'author-declared real'}. Run li run to refresh results.")
        else:
            result = load_input(args.input, args.as_of)
            matches = [r for r in result["records"] if r["id"] == args.id]
            if not matches:
                raise InboxError(f"MissingRecord: id {args.id!r}")
            r = matches[0]
            target = Path(args.input) / r["source"]["file"]
            if target.suffix.lower() == ".jsonl":
                lines = target.read_text(encoding="utf-8-sig").splitlines()
                raw = json.loads(lines[r["source"]["line"] - 1])
                raw["status"] = args.status
                lines[r["source"]["line"] - 1] = json.dumps(raw, ensure_ascii=False, sort_keys=True)
                text = "\n".join(lines) + "\n"
            else:
                values = json.loads(target.read_text(encoding="utf-8-sig"))
                for raw in values:
                    if raw["id"] == args.id:
                        raw["status"] = args.status
                text = json_text(values)
            atomic_write(target, text)
            print(f"Updated {args.id} to {args.status}. Run li run to refresh results.")
        return 0
    except (InboxError, OSError, UnicodeError) as e:
        print(str(e) if isinstance(e, InboxError) else f"IOError: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
