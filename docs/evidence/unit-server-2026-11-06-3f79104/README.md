# Unit-server clean-extraction verification

- Executor: Lu Wenxi.
- Run started: 6 November 2026, 12:56:04 UTC.
- Tested commit: `3f79104196643a4f58480c3e7422a656fd7849d8`.
- Server: `fit2109s2.rep.monash.edu`.
- Environment: Python 3.12.3, Git 2.43.0, Bash 5.2.21.
- Source ZIP SHA-256:
  `5c3db8ece530cc28d0d151b5a64f54a94106441beec0cbf286b6008b1eebe115`.

## Procedure and observed results

The transferred ZIP passed checksum and embedded-commit checks.
Its fresh extraction initially contained neither `.git` nor `.venv`.
Lu created a new Python 3.12 virtual environment and processed
requirements.txt using pip with --no-index.

Four Bash syntax checks completed successfully within a stop-on-error
wrapper. Individual syntax-check exit codes were not separately printed.
scripts/test.sh passed all 90 tests without skips in 7.481 seconds.
scripts/demo.sh produced the expected PASS/0 and FAIL/1 assessments
and returned 0 overall. The inventory program printed three records
and total quantity ten.

aggregate_eval.py recomputed the summary from the saved member records
and stored CI/unit-server outputs. The result matched summary.md
byte for byte. This comparison did not execute a new CI job.
No checker temporary directory remained. The wrapper completed with
VERIFICATION PASSED and verification_exit=0.

## Retained evidence and limits

The six accompanying files are copied unchanged from the server.
SHA256SUMS identifies the tested source project.zip; that ZIP is retained
as the original export rather than duplicated in this evidence folder.
This explanation was written after the run; verification.log retains
the original output.

ChatGPT prepared commands and helped interpret the evidence.
Lu executed the commands on the course server.
Independent evidence review by Chin Wen Hui is pending.
The result applies to the stated commit, not automatically to later changes.
