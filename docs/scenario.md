# Inventory report handoff scenario

## Workflow and pain point

A developer delivers an inventory-report project as a ZIP archive generated from a selected Git commit. The recipient extracts it and follows the README.

The report requires `data/items.csv`. A required input can exist in the developer's working directory without being included in the selected commit. Local execution may therefore succeed while the recipient's execution fails.

Handoff Check will compare declared required files with the selected commit and actual archive, helping developers identify omissions before delivery.

## Investigation and observed results

On 12 October 2026, Lu Wenxi constructed a controlled reproduction using the files in `scenarios/inventory-report`.

The normal version committed all four source files. The fault version used `git rm --cached` to stop tracking the CSV while retaining the local file. Both selected commits were archived and extracted into separate, newly created receiver directories.

This was a deliberately constructed experiment, not a claim that an earlier accidental handoff incident occurred.

Environment: macOS, Git 2.50.1 (Apple Git-155), Python 3.14.2.

| Observation | Normal commit `0bff84c` | Fault commit `b328b04` |
|---|---|---|
| Developer's local CSV exists | Yes | Yes |
| Developer's program exit code | 0 | 0 |
| Selected commit contains CSV | Yes | No |
| ZIP contains CSV | Yes | No |
| Receiver's program exit code | 0 | 1 |

The normal receiver printed `Records: 3` and `Total quantity: 10`. The fault receiver raised `FileNotFoundError` for `data/items.csv`.

Evidence:
- `docs/evidence/normal-receiver.txt`
- `docs/evidence/missing-receiver.txt`

The recorded commit IDs belong to Lu's independent experiment repository. The reproduction below creates new fixture commits; their IDs will differ.

## Independent reproduction

Prerequisites: Git and Python 3. Run these commands interactively from the group repository root. Do not enable automatic exit on errors: the final receiver failure is intentional.

### 1. Create an isolated fixture

```bash
handoff_project_dir="$PWD"
handoff_source_dir="$handoff_project_dir/scenarios/inventory-report"

mkdir -p "$handoff_project_dir/.scenario-runs"
handoff_run_dir="$(mktemp -d "$handoff_project_dir/.scenario-runs/run.XXXXXX")"

mkdir -p "$handoff_run_dir/repository/data"
mkdir "$handoff_run_dir/normal-receiver" "$handoff_run_dir/missing-receiver"

cp "$handoff_source_dir/.gitignore" "$handoff_run_dir/repository/"
cp "$handoff_source_dir/README.md" "$handoff_run_dir/repository/"
cp "$handoff_source_dir/report.py" "$handoff_run_dir/repository/"
cp "$handoff_source_dir/data/items.csv" "$handoff_run_dir/repository/data/"

cd "$handoff_run_dir/repository"

git init -b main
git config user.name "Scenario Fixture"
git config user.email "fixture@example.invalid"
git config commit.gpgsign false

git add .gitignore README.md report.py data/items.csv
git commit -m "Create normal scenario fixture"
```

The fixed identity is only for generated fixture commits. It does not change the contributor identity in the group repository.

### 2. Verify the normal handoff

```bash
python3 report.py
echo $?

git archive --format=zip -o "$handoff_run_dir/normal.zip" main
python3 -m zipfile -l "$handoff_run_dir/normal.zip"

python3 -m zipfile -e "$handoff_run_dir/normal.zip" "$handoff_run_dir/normal-receiver"

cd "$handoff_run_dir/normal-receiver"

python3 report.py
echo $?
```

Both executions should print `Records: 3` and `Total quantity: 10`, with exit code 0. The ZIP listing should include `data/items.csv`.

### 3. Construct and verify the faulty handoff

```bash
cd "$handoff_run_dir/repository"

git switch -c case-missing-input main
git rm --cached -- data/items.csv
git commit -m "Create missing-input scenario fixture"

python3 report.py
echo $?

git status --short --untracked-files=all
git ls-tree -r --name-only HEAD

git archive --format=zip -o "$handoff_run_dir/missing.zip" HEAD
python3 -m zipfile -l "$handoff_run_dir/missing.zip"

python3 -m zipfile -e "$handoff_run_dir/missing.zip" "$handoff_run_dir/missing-receiver"

cd "$handoff_run_dir/missing-receiver"

python3 report.py
echo $?

cd "$handoff_project_dir"
```

Expected results:
- Developer execution still succeeds with exit code 0.
- Git status reports `?? data/items.csv`.
- The selected commit and ZIP omit the CSV.
- Receiver execution raises `FileNotFoundError` and exits with code 1.

## Interpretation and current validation status

The controlled experiment demonstrates that successful local execution
does not establish required-file presence in the selected commit or ZIP.
It deliberately isolates a missing-input failure rather than claiming
an earlier accidental incident.

- Open limitation: the controlled reproduction validates the failure
  mechanism. Additional evidence of the team's investigation into this
  need in actual development has not yet been documented in the repository.
  This remains an open limitation.
- Scenario peer-review evidence is recorded in MR !2.
- The completed `scripts/demo.sh` reconstructs the normal and missing-file
  cases and checks the real tool's expected PASS/0 and FAIL/1 results.
- Frozen checker commit `71d7472` passed the then-current 45-test suite
  and demonstration locally and from a clean unit-server extraction on
  4 November 2026. The retained evidence is in
  `docs/evidence/local-real-checker-2026-11-04.txt` and
  `docs/evidence/unit-server-real-checker-2026-11-04.txt`, reviewed in MR !8.
- The measured comparison now contains 48 method runs from three members.
  Results, recording qualifications and sensitivity analyses are in
  `docs/evaluation.md` and `docs/evaluation-runs/summary.md`.
- Integrated commit `3f79104` passed clean-extraction unit-server
  verification on 6 November 2026: all 90 tests and the demonstration
  passed. Evidence is in
  `docs/evidence/unit-server-2026-11-06-3f79104/README.md`.
  Verification remains specific to the tested revision.

## Reproduction check — 13 October 2026

Lu Wenxi executed the independent reproduction instructions from the group repository. The generated normal fixture commit was `d383f50`, and the fault fixture commit was `a68d251`.

Both developer executions succeeded with exit code 0. The normal archive contained `data/items.csv`, and its receiver printed `Records: 3` and `Total quantity: 10`, with exit code 0. The fault archive omitted the CSV, and its receiver raised `FileNotFoundError`, with exit code 1.

The environment was macOS, Git 2.50.1 (Apple Git-155), and Python 3.14.2. Receiver outputs are recorded in `docs/evidence/reproduction-2026-10-13.txt`.

This 13 October check was performed by the original author.
It records the historical scenario reproduction, not final submission
verification. Subsequent evidence and remaining work are described in
the current validation status above.