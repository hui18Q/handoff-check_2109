# Reproducibility runs (evaluation.md §8.6)

Both runs used `scripts/repro_eval.sh` at project commit 24bcfbb with the frozen
checker 71d7472d7e920b2bba64327e9b69c3c18ecacd60.

| Run | Where | Python | Git | Bash |
|---|---|---|---|---|
| `ci/` | GitLab CI pipeline #168569, job `reproducibility` (project runner, python:3.12.16-slim) | 3.12.16 | 2.47.3 | 5.2.37 |
| `unit-server/` | fit2109s2.rep.monash.edu, fresh clone, new venv | 3.12.3 | 2.43.0 | 5.2.21 |

Result: all 8 cases identical in exit code, stdout (byte for byte), normalised
stderr and fixture commit IDs / ZIP hashes. Check with:

    diff -r -x environment.txt -x job.log ci unit-server

`ci/job.log` is the CI job output. Exit codes were 0 1 1 0 2 2 1 2 for cases 01–08,
matching the §3 expected outcomes, and all fixture identifiers match §2.3.
