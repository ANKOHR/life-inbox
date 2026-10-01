# Local build evidence

Measured on 2026-10-01 using Python 3.12.10 on this Windows CPU environment.

The installed li.exe entry point was invoked in three fresh processes: fixtures --out demo, run --input demo, report --format md. Full demo elapsed time: 0.676105 seconds, below the five-second acceptance limit. A separate report --format json process took 0.206191 seconds. Timings include process startup and captured output. These are measured computation timings, not personal time savings. Performance on other hardware is unmeasured.

The JSON report matched the independent expectations exactly: 200 total records; 50 each of idea, task, message and file; 50 each of inbox, active, done and archived; 13 overdue tasks. The overdue ID set matched all 13 planted cases, with zero false positives and zero missed cases. Both count partitions summed to 200. The Markdown report carried the synthetic provenance banner and record-level source references. No tracebacks occurred.

Installation used pip --no-deps --no-build-isolation --no-index -e . and no network calls. The local Python user scripts directory is absent from this machine's PATH, so the benchmark used the installed executable's absolute path. README documents the module fallback and PATH setup. No personal inputs were used.

pytest results and the implementation commit are recorded in BUILD-DONE.txt. Tests include corrupting source due dates, which changes computed overdue count from 13 to 0, and corrupting stored expectations, which leaves computed record total at 200. This is direct evidence against hardcoded output. Simulated atomic replacement failure preserves the previous report and removes temporary files, validating the immediate storage improvement.

Final product verdict remains deferred until the two-week real-use window. No real-use results, savings, or buyer evidence have been measured.
