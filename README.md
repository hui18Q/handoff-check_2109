## Setup and demonstration

Run from the extracted project root using Bash or a compatible shell.
Python 3.12 must already be installed.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python3 --version
python3 -m pip install -r requirements.txt

bash scripts/demo.sh
echo $?
```

Expected Python version: `Python 3.12.x`.

The Python checker is included. The demonstration creates two local
fixtures and checks the following outcomes:

| Demonstration case | Expected checker result | Expected checker exit code |
|---|---|---|
| Complete selected commit and generated ZIP | PASS | 0 |
| Required CSV exists locally but is absent from the selected commit and ZIP | FAIL | 1 |

The demonstration script returns 0 only when both checker exit codes
match these expectations. Its final success message is:

```text
Demo completed: both checker exit codes matched expectations.
```

## Handoff Check

Handoff Check assesses whether declared required regular files are present
in both a selected Git commit and a handoff ZIP archive.

Bash validates the command line and repository, resolves the selected
commit, retrieves the committed checklist, collects Git evidence, handles
the archive and invokes the Python checker.

Python is responsible for validating the checklist and archive, assessing
required files, and reporting findings.

PASS establishes required-file presence in the selected commit and ZIP.
It does not establish file-content equality, archive provenance or program
correctness.

## Requirements

- Bash.
- Git with ZIP archive support.
- Python 3.12, available as `python3` after virtual-environment activation.
- A writable project directory for temporary workspaces.

The current runtime, demonstration and isolated interface tests use Python
standard-library modules. No third-party package installation is needed
for the documented commands. `requirements.txt` records this explicitly;
any future third-party test dependencies must be version-pinned there.

## Full local regression checks

With the Python 3.12 virtual environment activated:

```bash
bash scripts/test.sh
echo $?
```

Expected: 90 test methods are discovered: six isolated Bash interface
tests, 40 real-checker/helper tests, 21 evaluation-fixture and edge-case tests,
and 23 aggregation tests. All 90 passed in the reviewed Linux environment;
the runner prints `OK` and returns 0. A filesystem-dependent non-UTF-8
filename test may be skipped where its fixture cannot be created; report
any skip explicitly. The suites use standard-library `unittest`.

Normal and failure assessments write reports to stdout. Invalid inputs
write an error to stderr and return 2, without a PASS/FAIL report. Each
required path reports working-tree, selected-commit and ZIP evidence.
Paths with newlines are escaped so findings remain readable.

The Python validation rules and design choices are documented in
`docs/python-checker.md`.

Run the tool only against repositories you are authorised to inspect.

## Isolated interface tests

With the Python 3.12 virtual environment activated:

```bash
python3 tests/test_bash_python_interface.py -v
echo $?
```

Expected result: all six test methods pass, the runner prints `OK`, and
the test process exits with 0. Execution time varies.

These tests build temporary Git fixtures and a temporary tool copy with
a controlled Python test double. They do not require the real checker
in the project's `src` directory.

They exercise checker argument delivery, selected-commit evidence,
supported exit codes, output streams, supplied ZIP handling, preservation
and cleanup.

Passing these tests does not establish the real checker's classification
or diagnostic correctness.

## Checker command

Display help without requiring the Python checker:

```bash
bash scripts/handoff_check.sh --help
```

Expected exit code: 0.

The public command is:

```text
bash scripts/handoff_check.sh --repo PATH \
    [--ref REF] [--checklist PATH] [--zip PATH]
```

- `--repo`: root of a local, non-bare Git working repository.
- `--ref`: selected commit or ref; defaults to `HEAD`.
- `--checklist`: repository-relative checklist path; defaults to
  `handoff-check.json`.
- `--zip`: optional existing ZIP, resolved from the caller's working
  directory. If omitted, Bash generates a temporary ZIP from the selected
  commit.

The checklist is read from the selected commit. Local checklist edits
are not used until committed and selected.

Example checklist:

```json
{
  "required_files": [
    "README.md",
    "report.py",
    "data/items.csv"
  ]
}
```

Required paths must be canonical repository-relative paths. ZIP entries
must match those paths exactly.

| Exit code | Meaning |
|---|---|
| 0 | PASS: all required regular files are present in the selected commit and ZIP. |
| 1 | FAIL: a required regular file is absent or has an unsupported type. |
| 2 | ERROR: invalid input or a required operation failed. |

See `docs/handoff-interface.md` for the detailed contract.

## Demonstration construction

`scripts/demo.sh` copies the submitted inventory example into a temporary
Git repository and creates two commits.

The first contains the README, program, checklist and required CSV.
The second removes the CSV from tracking and adds an ignore rule while
retaining the local CSV.

Both assessments select explicit commit IDs. The normal assessment
therefore also exercises selection of an earlier commit rather than the
fixture's current HEAD.

The demonstration requires no network access or existing project Git
history. Its temporary repository is created beneath `.scenario-runs/`
and removed when the script exits through its cleanup handler.

The example program can also be run independently:

```bash
python3 scenarios/inventory-report/report.py
```

Expected output:

```text
Records: 3
Total quantity: 10
```

## Current verification status — 6 November 2026

- The reviewed integrated snapshot is commit
  `075625db8834f14b83f46266b3475937fcd07fe3`. [Pipeline #169231](https://git.infotech.monash.edu/fit2109/fit2109-s2-2026/group-assignment/MY-T06-06/-/pipelines/169231)
  is displayed as passed. The configured default jobs run the tests and demonstration;
  the frozen-checker reproducibility job is separately triggered.
- An assistant-executed check of this snapshot's ZIP in a fresh Linux
  extraction using Python 3.12.14 passed all 90 tests and the demonstration.
  These checks are separate from contributor macOS execution and course
  unit-server verification.
- Lu Wenxi verified frozen checker commit `71d7472` locally and from a
  clean extraction on the unit server on 4 November. Both environments
  passed the then-current 45-test suite and demonstration. Evidence is in
  `docs/evidence/local-real-checker-2026-11-04.txt` and
  `docs/evidence/unit-server-real-checker-2026-11-04.txt`, reviewed in MR !8.
- Evaluation contains 48 method runs from three members. Results,
  qualifications, the 14-pair flagged-exclusion view and the additional
  six-pair sensitivity view are documented in `docs/evaluation.md`.
  The generated aggregate is `docs/evaluation-runs/summary.md`.
- Stored CI and unit-server outputs for the frozen checker match across
  all eight evaluation cases after documented path normalisation.
  Evidence is in `docs/evaluation-runs/reproducibility/`.
- Final clean-extraction verification of the submission revision on the
  course unit server remains pending. Earlier verification does not
  establish successful execution of every later integrated revision.

## Historical verification records

The entries below preserve earlier development-stage results and outstanding
work as recorded at the time. Their pending statements are superseded where
the current summary above records subsequent completion.


- The real checker was exercised locally on 28 October 2026 using Python
  3.12.14. The initial 32 test methods passed. Both real-checker demo cases
  produced their expected 0/1 exit codes and the demo returned 0.
- `docs/evidence/python-checker-2026-10-28.txt` records the exact source
  commit, commands, environment and actual local output. These local
  results do not replace final unit-server verification or peer review.
- A clean ZIP extraction of `c3c0675` was checked locally with a fresh
  Python 3.12.14 virtual environment and no Git history. All 32 tests and
  both real-checker demonstration cases passed. No temporary fixture or
  checker workspace remained. The full output is retained in
  `docs/evidence/python-clean-extraction-2026-10-28.txt`.
- The following earlier records describe the pre-checker snapshot and
  retain their original limited scope.

- A clean extraction of commit `d63f209` was checked on the unit server
  using a new Python 3.12.3 virtual environment, Bash 5.2.21 and Git 2.43.0.
  Both Bash syntax checks, CLI help, the inventory example and all six
  isolated interface test methods passed. Demo preflight returned the
  expected missing-checker exit code 2. Complete workflow verification
  remains pending.

- The inventory example ran successfully using Python 3.12.16.
- Local setup, inventory execution and all six isolated interface test
  methods were verified from a clean extraction of commit `917960b`
  on macOS using a newly created Python 3.12.16 virtual environment.
- Demonstration syntax validation passed.
- With the real checker absent, demonstration prerequisite validation
  returned ERROR with exit code 2.
- Demonstration fixture construction and complete assessments were not
  exercised in those historical pre-checker runs. They have now been
  exercised locally with the real checker as recorded above.
- Chin Wen Hui independently reviewed `77dc8fa` in MR !7, reproduced two
  blocking defects and requested changes. The follow-up adds 13 regression
  methods (45 total); all 45 passed locally, as did both demo cases. The
  fixes require her re-review before merge. Defensive input policies are
  documented separately for team confirmation in `docs/python-checker.md`.
- A clean ZIP export of fix commit `c1f8c45` was checked in a new Python
  3.12.14 virtual environment without Git history. All 45 tests, three Bash
  syntax checks and both demo cases passed, with no test/demo or temporary
  checker workspace remaining. Actual commands and output are retained in
  `docs/evidence/python-review-fixes-2026-10-28.txt`.
- Complete automated testing, CI integration, full unit-server workflow verification
  from a clean extraction, and evaluation against the manual baseline
  remain pending.

Local evidence is recorded in:

- `docs/evidence/bash-python-interface-2026-10-26.txt`
- `docs/evidence/demo-preflight-2026-10-27.txt`
- `docs/evidence/clean-extraction-preflight-2026-10-27.txt`
- `docs/evidence/unit-server-preflight-2026-10-28.txt`

AI assistance, human checks, review decisions and remaining risks are
recorded in `docs/ai-use.md`.
