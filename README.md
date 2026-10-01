# Life Inbox

One local capture point for ideas, tasks, messages and file references. A working Python CLI for Henry's school, outreach, builds and applications. All results are computed from explicit inputs. No network calls, model calls, GPU workloads, database server, or runtime dependencies.

## Quickstart

Requires Python 3.10+ and setuptools for installation. From this repository:

```powershell
python -m pip install --no-deps --no-build-isolation --no-index -e .
li fixtures --out demo
li run --input demo
li report --format md
```

If `li` is not found, add the Python user Scripts directory printed by pip to your shell PATH, or replace `li` with `python -m life_inbox.cli` in every example. Installation uses local build tools only and never fetches packages.

The fixture command requires an empty or nonexistent destination to prevent overwriting personal inputs. The shell-independent equivalent is `python -m life_inbox.cli`. Results are stored locally in `.life-inbox/results.json`. Use a separate state path per inbox:

```powershell
li --state personal-results.json run --input personal --as-of 2026-10-01
li --state personal-results.json report --format json --out personal-report.json
```

The reference date defaults to the fixed date `2026-09-30`. Always supply `--as-of` for real use. No implicit wall-clock dates affect results. Repeated runs with identical input files, filenames, and reference date produce byte-identical state and reports. Fixture construction uses no randomness, so there is no seed.

A five-record handwritten synthetic example is shipped in `examples/tiny`. Try `li run --input examples/tiny`, followed by `li report --format md`. It has five records and one overdue task.

## Subcommands

- `li fixtures --out demo`: generate 200 labelled synthetic records and independent expectations.
- `li run --input demo --as-of 2026-09-30`: validate every input and compute all counts and queue membership.
- `li report --format md`: render saved results with a provenance banner. JSON uses `--format json`; atomic file output uses `--out report.json`.
- `li capture --input personal --id application-1 --kind task --title "Submit application" --created 2026-10-01 --due 2026-10-05 --as-of 2026-10-01`: create a real, author-entered inbox record. Use `--synthetic` for illustrative captures. File references additionally need `--path "C:\Users\henry\Documents\CV.pdf"` and `--kind file`.
- `li triage --input personal --id application-1 --status active --as-of 2026-10-01`: update the source record's status. Capture and triage remind you to rerun `li run` to refresh saved results.

Every subcommand has `--help` and an example. `--state` is a global argument and must precede the subcommand. Successful commands return 0; named data, storage and I/O errors return 2. argparse also returns 2 for invalid command usage.

## Input format reference

Inputs are direct children of a directory, encoded as UTF-8 (optional BOM). Supported record formats are `.json` arrays and `.jsonl` with one object per line. JSONL permits blank lines and `#` header comments. YAML, CSV and other files cause a named SchemaError instead of being silently ignored. Nested directories are not traversed. `expectations.json` and `README.md` are reserved metadata names and never contribute records. Do not put real records in those names. An empty directory is a valid empty inbox.

```json
{
  "id": "application-1",
  "kind": "task",
  "title": "Submit application",
  "body": "Personal entry typed by Henry",
  "status": "inbox",
  "created": "2026-10-01",
  "due": "2026-10-05",
  "synthetic": false
}
```

Required fields:

| Field | Rule |
| --- | --- |
| id | Nonempty text, globally unique across input files |
| kind | idea, task, message, file |
| title | Nonempty text |
| status | inbox, active, done, archived |
| created | Canonical YYYY-MM-DD, no later than as_of |
| synthetic | Explicit JSON boolean; false means author-declared real |

Optional fields: `body` is text; `due` is a canonical date allowed only for tasks; `path` is text, required only for files and forbidden on other kinds. Every text field has a 100,000-character limit. Unicode and Windows paths are supported. U+2014 characters are rejected with a field-specific error; use a hyphen. File paths are stored as references, never opened, executed, verified or copied. Files need not exist. Capture supports an explicit initial `--status`, defaulting to inbox. Unknown fields, including amounts, are rejected; this tool does not account for money. Future due dates are legitimate planned tasks; future created dates are rejected. Due dates earlier than created dates are retained as explicitly entered obligations.

Classification is deliberately simple: the inbox queue contains exactly status=inbox records. Overdue tasks are exactly task records with status inbox or active and a supplied due date strictly before as_of. Due today, future due, undated, done and archived tasks are never overdue. Counts by kind and by status each reconcile to total. IDs and records are sorted by ID using Python Unicode ordering. No priority guessing, automatic categorisation, message sending or semantic deduplication occurs. Triage permits any transition among the four documented statuses.

## Architecture

```text
JSON / JSONL inputs -> cli.load_input -> core.validate + core.workflow
                                         |
                                         v
                              atomic local results.json
                                         |
                                         v
                          report.render -> Markdown / JSON

fixtures.records + independent expectations -> synthetic demo inputs
capture / triage -> validated source file changes -> rerun workflow
```

`core.py` contains pure domain logic. `cli.py` isolates filesystem reads, atomic writes, argument parsing and named errors. `fixtures.py` constructs labelled planted records. `report.py` renders deterministic reports. Every CLI-loaded report record carries the source filename and line; JSON array schema errors refer to line 1, while JSON parse errors and JSONL record errors identify their exact line. Reports provide all contributing records and explicit overdue/inbox IDs, allowing every count to be checked by hand.

## Honesty boundary

The tool computes from inputs. It does not discover, predict, estimate or infer missing facts. Reports distinguish synthetic records from author-declared real records. A `synthetic:false` flag is the author's claim, not an independent verification that Henry owns the data. There is no real personal data shipped with this project. Real trial results must stay local and must not be committed or published.

Time saved and money saved are unmeasured: no baseline is supplied and no savings are claimed. No hypothetical numeric benefit is displayed. Local benchmark durations in EVIDENCE.md are measured computation timings, not time savings or estimates of personal value. The fixture validates deterministic classification, not real-world usefulness.

## Fixture labelling policy and ground truth

`records.jsonl` starts with a SYNTHETIC header and every record has `synthetic:true` plus a synthetic title/body. `expectations.json` has `synthetic:true` and a textual SYNTHETIC label; JSON has no header comment syntax. Fixture README files carry a SYNTHETIC HTML header comment. The five-record JSONL example follows the same policy. Every report carries a provenance banner.

The 200-record fixture repeats four kinds 50 times each. In block b of four records, status is `(b + position) modulo 4`, with positions idea=0, task=1, message=2, file=3, and statuses inbox=0, active=1, done=2, archived=3. Each status totals 50. Tasks in even blocks have past due dates; tasks in odd blocks have future due dates. Only blocks divisible by four contain both a past-due and open task, all active: 13 blocks (0 through 48). Overdue IDs are 001, 017, 033, 049, 065, 081, 097, 113, 129, 145, 161, 177, 193. The expectations are independently written constants, never loaded by the workflow. Tests corrupt input dates and expectations separately to prove that reports depend on records rather than stored answers.

## Tests, evidence and acceptance criteria

```powershell
python -m pytest -q
```

The suite checks all named brief requirements, exact counts and queue membership, no false positives or missed planted cases, empty inputs, malformed formats, Unicode/long text, future dates, schema drift, duplicate IDs, deterministic bytes, real CLI execution, source triage, atomic replacement failures and previous-result preservation. See EVIDENCE.md for the measured installed CLI demo timing and local acceptance results. BUILD-DONE.txt records the test count and local implementation commit.

Hypothesis: deterministic validation and explicit classification can make a trustworthy capture and triage tool. Acceptance: all planted cases found with zero false positives, totals reconcile exactly, the 200-record demo and report finish under five seconds, and all tests pass. The real-user utility hypothesis remains untested until the trial below.

## Failure modes and limits

- Malformed JSON: ParseError naming file and exact line. Unsupported formats and schema drift: SchemaError naming file, line and offending field.
- Missing directory or saved results: MissingInput with a usage hint. Duplicate IDs reject the entire run without replacing prior results.
- Bad report output path: WriteError; sibling temporary files are removed and an existing destination remains intact if replacement fails. Each individual write is atomic, but fixture generation across three files is not a multi-file transaction.
- Concurrent writers are unsupported. Atomic replacement prevents partial files but cannot prevent competing captures from losing an update. Use one CLI writer at a time.
- Result files are snapshots. Rerun after capture, triage, editing input, or changing as_of. Report revalidates saved records and recomputes counts before rendering.
- No attachments are imported, no reminders are delivered, and no money is tracked. References and user-entered labels are trusted only to the extent described above.

## Two-week evidence-based improvement hook

Begin the window on Henry's first real capture, not the build date. Keep daily trial notes locally, outside this repository: trial date, CLI use count and hand-checked sample IDs, expected kind/status/overdue/inbox membership, computed membership, and mismatched-record count. Primary metric is record-level classification error: records with any incorrect membership or classification divided by records hand-checked. Review all records when fewer than 20 are available, otherwise a declared sample of at least 20. Zero sampled records means accuracy unmeasured, never zero error.

After 14 calendar days, if error exceeds 10 percent, identify and fix the leading cause, then rerun the labelled sample. If the tool is not used, record the non-use reason and kill it. If measuring time saved instead, record matched manual and CLI workflows against the same input and subtract measured timings; do not infer savings from CLI runtime alone.

The immediate build improvement was to preserve prior outputs on failed writes and pin that behavior with a simulated replacement-failure test. This local engineering evidence is separate from the required two-week real-use decision.

## Verdict

Deferred pending the two-week real-use evidence window. No verdict or usage evidence is fabricated. Record the final verdict and reason in VERDICT.md: expand if daily use or revenue warrants it; integrate if it heavily overlaps a sibling project; commercialise if a buyer would pay for it as-is; maintain for portfolio evidence otherwise; kill if unused or unable to meet acceptance criteria. The build is ready for a local trial; publishing to ANKOHR/life-inbox is handled separately and was not performed here.
