# Evaluation: Handoff Check versus the manual baseline

Status: **measured.** Results are in Sections 8–9; Sections 2–7 are unchanged
except for the changes logged in Section 10.
Owner: Chin Wen Hui (fixture author). Expected-outcome checker: Lu Wenxi.
Binding source: project proposal Sections 3–5.

This document fixes the fixtures, the expected outcomes, both procedures,
the counting and timing rules and the run order **before** either method is
measured. Results and raw logs are added later in Sections 8–9 without
changing Sections 2–7. Any later change to the protocol must be listed in
Section 10 with its date and reason.

## 1. What is compared

| | Manual baseline | Handoff Check |
|---|---|---|
| Inputs | same repository, target ref, `handoff-check.json` and ZIP | same |
| Decision rules | Section 4.1 | Section 4.1 (implemented by the tool) |
| Evidence | `git rev-parse`, `git show`, `git status`, `git ls-tree`, `git archive`, `python3 -m zipfile -l` | `scripts/handoff_check.sh` report and exit code |
| Out of scope | receiver execution (separate scenario check, proposal §5) | same |

## 2. Fixtures

### 2.1 Generator

`scripts/make_fixtures.py` (Python 3.12 standard library + Git) builds all
eight proposal §4 cases. *The location is a proposal; Lu Wenxi must agree to
it, because `scripts/demo.sh` may later call the same generator.*

Each case is a separate one-commit repository:

```text
.scenario-runs/eval-fixtures/        (gitignored via /.scenario-runs/)
  manifest.json                      commit IDs, ZIP SHA-256, commands
  case-NN/
    INPUTS.txt                       target ref, checklist, ZIP, checker command
    repo/                            the Git repository under assessment
    handoff.zip                      supplied ZIP (cases 07 and 08 only)
    manual-handoff.zip               created by the manual baseline (other cases)
```

Case directories use neutral names and contain no expected outcome, so the
directory alone does not reveal the answer.

Determinism: file contents are fixed LF bytes; Git runs with system and
global configuration disabled, `core.autocrlf=false`, no hooks and no
signing; author and committer are `Handoff Fixture <fixture@example.invalid>`
at `2026-10-20T10:00:00+11:00`; supplied ZIPs use fixed timestamps, Unix
`0644` modes and no compression. Requires Git ≥ 2.32. Unit server Git
2.43.0 (confirmed by Lu Wenxi, 2026-11-04). Running the generator on the
unit server, and obtaining the Section 2.3 identifiers there, is not yet
verified.

### 2.2 Reproduction commands

From the project root, inside the Python 3.12 virtual environment:

```bash
python3 --version                          # must print Python 3.12.x
rm -rf .scenario-runs/eval-fixtures        # only if a previous copy exists
python3 scripts/make_fixtures.py
```

The generator refuses to overwrite an existing output directory and refuses
any `--output` outside the project. Every member regenerates the fixtures
immediately before their own session (excluded from timing), then checks
that the printed commit IDs equal Section 2.3.

### 2.3 Reference identifiers

Produced identically by two independent runs on 2026-11-04 (Python 3.12.16
and Python 3.14.4, Git 2.53.0, Linux/WSL2).

| Case | Target ref | Commit on `main` | Supplied ZIP SHA-256 |
|---|---|---|---|
| case-01 | `main` | `92f067b25ee433ac8b5931dd33b254e65e72581b` | — |
| case-02 | `main` | `68edbabdc81c7325b2088dbb95a0fd352ff36876` | — |
| case-03 | `main` | `b48d716ebb570b4c4e419d940652de922ce1a8fb` | — |
| case-04 | `main` | `d7d3a9dd32a41a550eec314cee9faf4ea8821d43` | — |
| case-05 | `main` | `df81a70abb2df6fb63ccd65bf1b91a7e7e1953d4` | — |
| case-06 | `v1.0` | `b7e74af8afc475937da3e91c519828ece6b71414` | — |
| case-07 | `main` | `65476cfa6ddead9da2d38752e3b744bc752e2293` | `4d5745dfba9f0075bae111c89987782952a952b547f903c9d32d8f8e7de5d81e` |
| case-08 | `main` | `d3c40e761dc83c9c4b5939a094eb58454fce7ded` | `64bfb1a5af12db736b33f719f7bdd6a27af37735d906579f65084058480ff17f` |

### 2.4 Case construction

All cases share the same small project (`README.md`, `report.py`,
`data/items.csv`) and, except case 05, the same checklist:

```json
{ "required_files": ["README.md", "report.py", "data/items.csv"] }
```

| Case | Proposal §4 case | Construction |
|---|---|---|
| case-01 | complete handoff | All four files committed. |
| case-02 | required file left untracked | `data/items.csv` exists in the working tree but was never added. |
| case-03 | required file omitted by `export-ignore` | All files committed plus `.gitattributes`: `data/items.csv export-ignore`. |
| case-04 | unrelated untracked file (+ ignored file) | Complete commit with `.gitignore`: `*.log`; untracked `notes/todo.txt`; ignored `report.log`. |
| case-05 | malformed checklist | All files committed; checklist entry 3 is `"../data/items.csv"` (parent traversal). |
| case-06 | invalid ref | Complete commit; target ref `v1.0` was never created. |
| case-07 | supplied ZIP missing a required file present in the commit | Complete commit; supplied `handoff.zip` contains `README.md`, `report.py`, `handoff-check.json` only. |
| case-08 | invalid ZIP archive | Complete commit; supplied `handoff.zip` is a valid ZIP truncated to half its length. |

Case 05 uses one malformed-checklist variant (parent traversal). The other
rejected forms (absolute, duplicate, non-string, invalid JSON) are covered by
the automated test suite, not by this effort comparison.

## 3. Expected outcomes

Derived from the proposal rules (§3) by Chin Wen Hui when the fixtures were
designed, before any measured run. Lu Wenxi checks each row independently
against the checklist and actual Git behaviour and ticks the last column
(proposal §5). If Lu disagrees, the row is discussed and the decision is
logged in Section 10; a row is never changed to match a tool output.

All eight rows checked by Lu Wenxi on 2026-11-04 (MR !10 follow-up review of
commit aa6de9c, checker 71d7472; evidence attached to MR !10:
`expected-outcome-evidence.txt`, `fixture-generation.txt`).

| Case | Verdict | Exit | Missing path / invalid input | Where absent | Context that must not cause FAIL | Expected next action | Proposal rule | Checked by Lu Wenxi |
|---|---|---|---|---|---|---|---|---|
| case-01 | PASS | 0 | — | — | none | none | §3 PASS definition | ☑ |
| case-02 | FAIL | 1 | `data/items.csv` | selected commit **and** archive | `data/items.csv` is `??` locally (evidence, not a pass) | add and commit `data/items.csv`, select the new commit, rebuild the ZIP | §3 "missing from the target tree … will fail" | ☑ |
| case-03 | FAIL | 1 | `data/items.csv` | archive only (in commit as `100644`) | — | remove the `export-ignore` rule for `data/items.csv`, commit, rebuild the ZIP | §3 "missing from … archive will fail" | ☑ |
| case-04 | PASS | 0 | — | — | `notes/todo.txt` (`??`), `report.log` (`!!`) | none | §3 "unrelated untracked or ignored files … will not automatically fail" | ☑ |
| case-05 | ERROR | 2 | checklist entry 3 `"../data/items.csv"` (parent traversal) | — (no PASS/FAIL verdict) | — | correct the entry to `data/items.csv` and commit the checklist | §3 checklist validation | ☑ |
| case-06 | ERROR | 2 | target ref `v1.0` does not resolve | — (no PASS/FAIL verdict) | — | select an existing commit/ref or create the tag | §3 ERROR = invalid input | ☑ |
| case-07 | FAIL | 1 | `data/items.csv` | supplied archive only (in commit) | — | rebuild the ZIP from the selected commit (or add the file to it) | §3 supplied-ZIP presence; §4 "must produce FAIL (exit 1)" | ☑ |
| case-08 | ERROR | 2 | supplied `handoff.zip` is not a readable ZIP | — (no PASS/FAIL verdict) | — | re-create or re-copy the archive | §3 "invalid or unreadable archives will produce ERROR" | ☑ |

Verification evidence for the checker (expected listings, from the 2026-11-04
dry run of the Section 4 commands):

| Case | `git status --short --untracked-files=all --ignored` | `git ls-tree -r REF` paths | `python3 -m zipfile -l` entries |
|---|---|---|---|
| case-01 | (empty) | README.md, data/items.csv, handoff-check.json, report.py | README.md, data/, data/items.csv, handoff-check.json, report.py |
| case-02 | `?? data/items.csv` | README.md, handoff-check.json, report.py | README.md, handoff-check.json, report.py |
| case-03 | (empty) | .gitattributes, README.md, data/items.csv, handoff-check.json, report.py | .gitattributes, README.md, **`data/`** (directory only), handoff-check.json, report.py |
| case-04 | `?? notes/todo.txt`, `!! report.log` | .gitignore, README.md, data/items.csv, handoff-check.json, report.py | .gitignore, README.md, data/, data/items.csv, handoff-check.json, report.py |
| case-05 | (empty) | README.md, data/items.csv, handoff-check.json, report.py | (not reached: ERROR at M2) |
| case-06 | (not reached) | `fatal: Not a valid object name v1.0` | (not reached: ERROR at M1) |
| case-07 | (empty) | README.md, data/items.csv, handoff-check.json, report.py | README.md, report.py, handoff-check.json |
| case-08 | (empty) | README.md, data/items.csv, handoff-check.json, report.py | `zipfile.BadZipFile: File is not a zip file` |

All committed modes are `100644` (regular file).

## 4. Manual baseline procedure

### 4.1 Decision rules (both methods)

Apply in this order; the first rule that applies decides.

1. Target ref does not resolve to a commit → **ERROR**.
2. Checklist is not a JSON object with a non-empty `required_files` array, or
   any entry is not a non-empty string, is absolute, contains an empty, `.` or
   `..` component, or duplicates another entry → **ERROR**.
3. The archive cannot be read as a ZIP → **ERROR**.
4. Any required path is not a regular file (`100644`/`100755`) in the selected
   commit, or has no exact file entry in the archive → **FAIL**. A directory
   entry such as `data/` does not satisfy `data/items.csv`.
5. Otherwise → **PASS**.

Unrelated untracked (`??`) or ignored (`!!`) paths are context and never
cause FAIL. Working-tree presence never substitutes for commit or archive
presence.

### 4.2 Start state

- Python 3.12 virtual environment active; fixtures regenerated (Section 2.2).
- Terminal in `.scenario-runs/eval-fixtures/case-NN/repo`.
- `../INPUTS.txt` already read; `REF` and `ZIP` noted from it.
- This section open; commands may be copied from here.

### 4.3 Commands and judgement points

Commands (M) are run in order. Judgement points (J) are the decisions the
evaluator makes from the output; each one is counted. `n` is the number of
checklist entries (3 for every case), `k` the number of status lines for
non-required paths.

| Step | Command | Judgement points (count) | Stop? |
|---|---|---|---|
| M1 | `git rev-parse --verify REF^{commit}` | **J1** ref resolves to a commit? (1) | No → ERROR, go to M6 |
| M2 | `git show REF:handoff-check.json \| python3 -m json.tool` | **J2** valid JSON object with non-empty `required_files` array? (1)<br>**J3** each entry valid per rule 2? (n) | any No → ERROR, go to M6 |
| M3 | `git status --short --untracked-files=all --ignored` | **J4** status of each required path noted as evidence (n)<br>**J5** each other listed path classified as unrelated context (k) | — |
| M4 | `git ls-tree -r REF` | **J6** each required path present with mode `100644`/`100755`? (n) | — |
| M5a | only if no ZIP is supplied: `git archive --format=zip -o ../manual-handoff.zip REF` | — | — |
| M5b | `python3 -m zipfile -l ZIP` (`../handoff.zip` or `../manual-handoff.zip`) | **J7** archive readable? (1)<br>**J8** each required path listed as an exact file entry? (n) | J7 No → ERROR, go to M6 |
| M6 | (record in results sheet) | **J9** verdict by rules 1–5 (1)<br>**J10** FAIL: missing path recorded (1 per missing path); ERROR: which input or command is invalid (1)<br>**J11** FAIL: where the missing path is absent — commit, archive or both (1 per missing path)<br>**J12** FAIL: next action for the missing path (1 per missing path) | stop timer |

`git archive -o` must write to `../`, never inside `repo/`; a ZIP inside the
working tree would itself appear as an untracked file.

Known limit of this baseline: `python3 -m zipfile -l` shows names and sizes,
not file types, so a symlink entry would look like a regular file. No
evaluation fixture contains one.

### 4.4 Counting rules

- **Commands**: every command line executed, including mistyped or repeated
  ones; a pipeline counts as one. Not counted: `cd`, `clear`, reading
  `INPUTS.txt`, starting/stopping the timer.
- **Judgements**: every J point actually made, including repeated checks. An
  extra judgement not in the table (e.g. re-checking a path) is counted and
  described in the notes column.

Counting rationale. Judgements fall into two groups:

- **Shared recording judgements**, counted identically for both methods:
  verdict (J9 / K1), missing path (J10 / K2a), location (J11 / K2b), next
  action (J12 / K2c), invalid input for ERROR (J10 / K3) and each context
  line (J5 / K4). Both methods must record these to complete a case.
- **Manual-only intermediate checks**, J1–J4 and J6–J8: validating the ref
  and checklist, noting required-path status, and checking each required path
  in the commit and archive. This is the inspection work the checker performs
  automatically, so the judgement difference between the methods comes from
  these points only.

In the table below, checker judgements equal the shared count; manual
judgements equal the shared count plus the manual-only checks (15, 15, 15,
15, 5, 1, 15 and 12 for cases 01–08).

Procedure minimum per case (reference only; record what actually happened):

| Case | Manual commands | Manual judgements | Checker commands | Checker judgements |
|---|---|---|---|---|
| case-01 | 6 | 16 | 2 | 1 |
| case-02 | 6 | 19 | 2 | 4 |
| case-03 | 6 | 19 | 2 | 4 |
| case-04 | 6 | 18 | 2 | 3 |
| case-05 | 2 | 7 | 2 | 2 |
| case-06 | 1 | 3 | 2 | 2 |
| case-07 | 5 | 19 | 2 | 4 |
| case-08 | 5 | 14 | 2 | 2 |

## 5. Handoff Check procedure

Start state: Python 3.12 virtual environment active; fixtures regenerated;
terminal in the checker worktree `../checker-71d7472` (Section 5.1);
`INPUTS.txt` read.

| Step | Command | Judgement points (count) |
|---|---|---|
| C1 | the checker command from `INPUTS.txt`, e.g.<br>`bash scripts/handoff_check.sh --repo …/case-NN/repo --ref REF --checklist handoff-check.json [--zip …/handoff.zip]` | — |
| C2 | `echo $?` | **K1** verdict and exit code read and consistent (1)<br>**K2a** FAIL: missing path recorded from each finding (1 per finding)<br>**K2b** FAIL: location recorded from each finding (1 per finding)<br>**K2c** FAIL: next action recorded from each finding (1 per finding)<br>**K3** ERROR: invalid input identified from the message (1)<br>**K4** each context line confirmed as not affecting the verdict (1 per line) |

Counting is deliberately conservative towards the checker: reading and
recording the report counts as a judgement even when the report states the
answer directly.

The checker version is fixed for all measured runs (Section 5.1).

### 5.1 Assessed implementation

All measured runs use one checker version: commit
`71d7472d7e920b2bba64327e9b69c3c18ecacd60`, reviewed and approved in MR !7.
Each participant creates a worktree at that exact commit, from the project
root:

```bash
git fetch origin
git worktree add ../checker-71d7472 71d7472d7e920b2bba64327e9b69c3c18ecacd60
```

Checker commands (C1, C2) are run from `../checker-71d7472`. Each raw-log
block records the output of:

```bash
git -C ../checker-71d7472 rev-parse HEAD
```

Measurement does not switch versions, even if MR !7 or later checker changes
are merged while measurement is in progress.

## 6. Timing

- **Start**: case directory open, `INPUTS.txt` read, first command typed or
  pasted and ready; the timer starts when that command is executed.
- **Stop**: verdict **and** diagnostic evidence (missing path, location and
  next action for FAIL; invalid input for ERROR) are written in the results
  sheet.
- **Excluded**: fixture generation, environment setup, reading this protocol,
  the gap between the two methods.
- Use a stopwatch; record whole seconds.

## 7. Method order

Each member performs both methods on every case, back to back. The first
method alternates from case to case, and the case sequence is rotated between
members. Result: every member does each method first 4 times (12/12 overall),
every case is seen manual-first by at least one member and checker-first by
at least one member, and no case is in the same sequence position for two
members.

M = manual baseline first, then checker. C = checker first, then manual.

| Position | Lu Wenxi | Yin Jiayu | Chin Wen Hui |
|---|---|---|---|
| 1 | case-01 M | case-04 M | case-07 C |
| 2 | case-02 C | case-05 C | case-08 M |
| 3 | case-03 M | case-06 M | case-01 C |
| 4 | case-04 C | case-07 C | case-02 M |
| 5 | case-05 M | case-08 M | case-03 C |
| 6 | case-06 C | case-01 C | case-04 M |
| 7 | case-07 M | case-02 M | case-05 C |
| 8 | case-08 C | case-03 C | case-06 M |

Per-case split (manual-first : checker-first): odd-numbered cases 1:2,
even-numbered cases 2:1.

## 8. Results

All figures come from the members' derived records
(`docs/evaluation-runs/<member>/results-analysis.csv`, joined with each member's
`results.csv` for the diagnosis fields). The method-level summary, the
excluding-flagged-pairs view and the §8.6 comparison are printed by
`scripts/aggregate_eval.py` and saved as `docs/evaluation-runs/summary.md`:

    python3 scripts/aggregate_eval.py \
      --repro docs/evaluation-runs/reproducibility/ci docs/evaluation-runs/reproducibility/unit-server

The script does not print the per-case tables in 8.2–8.5. These were computed
from the same derived files: each cell covers the three members' runs for one case
and method, giving the median with the minimum and maximum, and the first/second
medians split by the `order` column. The sensitivity figures that exclude a member
come from the same script with `--exclude-member`.

### 8.1 Run sheet

The 48 rows are kept per member rather than copied here:
`docs/evaluation-runs/<member>/results.csv` holds each member's original record,
and `results-analysis.csv` beside it is the derived file used for analysis
(expected verdict, log exit code, reconstructed judgement count and flags).
Raw logs are unchanged. Revisions to a member's `results.csv` are traceable in Git
history (for example, Lu Wenxi's d3ed67f added reconstructed judgement counts and
corrected four durations). Corrections made for analysis appear only in the
derived file and in each member's `README.md`.

| Member | Runs | Flags |
|---|---|---|
| Lu Wenxi (L) | 16 | `time-corrected`: case-01 and case-02, both methods |
| Yin Jiayu (Y) | 16 | `ai-assisted`: all 16 (ChatGPT assisted during timing, `yin/README.md`); `time-inconsistent`: case-01, case-02, case-08 manual |
| Chin Wen Hui (C) | 16 | none; three checker verdicts recorded as FAIL for logged exit 2 are corrected from the logs in the derived file (`chin/README.md`) |

The excluding-flagged-pairs view drops both methods of any flagged member-case and
leaves 14 pairs (L and C). Not every disclosed deviation is a flag. Chin Wen Hui's
block-pasted manual commands and FAIL-for-ERROR recordings are disclosed but not
flagged, so all 16 of those runs remain in the 14-pair view. A further sensitivity
view also excludes Chin Wen Hui (`--exclude-member chin`). That leaves Lu Wenxi's
six unflagged pairs: both methods 6/6 correct, and medians of 5 against 2 commands,
16 against 2.5 judgements and 34 s against 25 s (manual against checker).

### 8.2 Measure 1: correctness

| Case | Expected | Checker matches (L / Y / C) | Manual matches (L / Y / C) |
|---|---|---|---|
| case-01 | PASS | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ |
| case-02 | FAIL | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ |
| case-03 | FAIL | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ |
| case-04 | PASS | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ |
| case-05 | ERROR | ✓ / ✓ / ✓ | ✓ / ✓ / ✗ |
| case-06 | ERROR | ✓ / ✓ / ✓ | ✓ / ✓ / ✗ |
| case-07 | FAIL | ✓ / ✓ / ✓ | ✓ / ✓ / ✓ |
| case-08 | ERROR | ✓ / ✓ / ✓ | ✓ / ✓ / ✗ |

Checker verdicts are taken from the logged exit code. Chin Wen Hui's three
manual misclassifications recorded ERROR cases as FAIL; the same runs still named
the invalid input (8.4).

### 8.3 Measure 2: false alarms

| Case | Unrelated path | Checker treated as failure? (L / Y / C) | Manual treated as failure? (L / Y / C) |
|---|---|---|---|
| case-04 | `notes/todo.txt` (`??`) | no / no / no | no / no / no |
| case-04 | `report.log` (`!!`) | no / no / no | no / no / no |

All six case-04 runs returned PASS.

### 8.4 Measure 3: diagnosis

FAIL cases (missing-file diagnosis):

| Case | Method | Names missing path? | Correct location (commit / archive / both)? | Next action given? |
|---|---|---|---|---|
| case-02 | checker | 3/3 | 3/3 | 3/3 |
| case-02 | manual | 3/3 | 3/3 | 3/3 |
| case-03 | checker | 3/3 | 3/3 | 3/3 |
| case-03 | manual | 3/3 | 3/3 | 3/3 |
| case-07 | checker | 3/3 | 3/3 | 3/3 |
| case-07 | manual | 3/3 | 3/3 | 3/3 |

ERROR cases:

| Case | Method | Identifies the invalid input? |
|---|---|---|
| case-05 | checker | 3/3 |
| case-05 | manual | 3/3 |
| case-06 | checker | 3/3 |
| case-06 | manual | 3/3 |
| case-08 | checker | 3/3 |
| case-08 | manual | 3/3 |

### 8.5 Measure 4: effort

| Case | Method | Commands (median, min–max) | Judgements (median, min–max) | Time s (median, min–max) | Time when first (median) | Time when second (median) |
|---|---|---|---|---|---|---|
| case-01 | checker | 2 (2–4) | 1 (1–1) | 45 (25–76) | 60.5 | 25 |
| case-01 | manual | 6 (6–6) | 16 (11–16) | 40 (40–175) | 40 | 107.5 |
| case-02 | checker | 2 (2–2) | 4 (4–4) | 38 (25–48) | 25 | 43 |
| case-02 | manual | 6 (6–6) | 19 (12–19) | 38 (37–134) | 85.5 | 38 |
| case-03 | checker | 2 (2–2) | 4 (4–4) | 31 (24–39) | 35 | 24 |
| case-03 | manual | 6 (6–6) | 19 (14–19) | 40 (30–129) | 40 | 79.5 |
| case-04 | checker | 2 (2–4) | 3 (3–3) | 29 (24–57) | 24 | 43 |
| case-04 | manual | 6 (6–10) | 18 (14–18) | 40 (33–156) | 94.5 | 40 |
| case-05 | checker | 2 (2–2) | 2 (2–2) | 32 (25–47) | 39.5 | 25 |
| case-05 | manual | 2 (2–6) | 7 (7–19) | 29 (26–89) | 26 | 59 |
| case-06 | checker | 2 (2–4) | 2 (2–2) | 28 (25–68) | 25 | 48 |
| case-06 | manual | 2 (1–6) | 3 (3–5) | 30 (23–129) | 79.5 | 23 |
| case-07 | checker | 2 (2–2) | 4 (4–4) | 48 (27–50) | 49 | 27 |
| case-07 | manual | 5 (5–5) | 19 (19–19) | 40 (35–129) | 35 | 84.5 |
| case-08 | checker | 2 (2–2) | 2 (2–2) | 48 (26–50) | 26 | 49 |
| case-08 | manual | 5 (5–15) | 14 (14–16) | 61 (33–128) | 94.5 | 33 |

Effort medians over all 24 runs per method: commands 6 manual vs 2 checker,
judgements 16 vs 2.5, time 40 s vs 35 s. Excluding flagged pairs (14 per method):
commands 6 vs 2, judgements 18 vs 2.5, time 34 s vs 28.5 s. Yin Jiayu's manual times
(median 129 s) are three to four times the other members' and include
AI-assisted interaction, so time is reported as indicative only.

### 8.6 Measure 5: reproducibility

Same fixtures and Python 3.12 in both environments. GitLab CI and the unit
server both run the frozen checker commit
`71d7472d7e920b2bba64327e9b69c3c18ecacd60` (Section 5.1). The final
submitted project is re-checked separately from a clean `git archive`
extraction before submission.

| Case | GitLab CI exit | Unit server exit | stdout identical? | stderr identical after normalisation? |
|---|---|---|---|---|
| case-01 | 0 | 0 | yes | yes |
| case-02 | 1 | 1 | yes | yes |
| case-03 | 1 | 1 | yes | yes |
| case-04 | 0 | 0 | yes | yes |
| case-05 | 2 | 2 | yes | yes |
| case-06 | 2 | 2 | yes | yes |
| case-07 | 1 | 1 | yes | yes |
| case-08 | 2 | 2 | yes | yes |

Run on 2026-11-06 with `scripts/repro_eval.sh` at project commit 24bcfbb:
GitLab CI pipeline #168569 (Python 3.12.16, Git 2.47.3, Bash 5.2.37) and the
unit server `fit2109s2.rep.monash.edu` (Python 3.12.3, Git 2.43.0, Bash 5.2.21).
All eight cases were identical, and the fixture commit IDs and ZIP hashes in
both environments equal Section 2.3. Raw outputs are in
`docs/evaluation-runs/reproducibility/`.

Normalisation for comparison: replace the fixture root with `<FIXTURES>` and
`.handoff-tmp.XXXXXXXX` with `<TMP>` (case-05's error message names the
temporary checklist copy). stdout is compared byte for byte. Record the
Python, Git and Bash versions of both environments.

Separate integrated-project verification: on 6 November 2026, Lu Wenxi
verified commit `3f79104` from a fresh ZIP extraction on the course unit
server using Python 3.12.3. All 90 tests and the demonstration passed,
and recomputing the summary from the saved records produced an exact
match. This is separate from the frozen-checker CI/server comparison
above. Original evidence and limitations are in
`docs/evidence/unit-server-2026-11-06-3f79104/README.md`.

### 8.7 Improvement criterion (proposal §5)

The checker is an improvement if it matches every expected outcome, produces
no false FAIL for unrelated files, and needs fewer commands and judgements than
the manual baseline. Timing is reported as indicative only.

Result: on the recorded measures, the criterion is met for correctness, false
alarms, commands and judgements. The checker matched all 24 expected outcomes
against 21 of 24 for the manual baseline and produced no false FAIL. The records
show a median of 2 commands and 2.5 judgements per case against 6 and 16. The same
direction holds in the excluding-flagged-pairs view. Without Chin Wen Hui's runs,
both methods were fully correct, so the correctness difference rests on one
participant's runs; the effort difference in commands and judgements remains.

These figures describe the records, not unassisted human effort. One member's
runs were AI-assisted during timing. Some command counts include repeats that the
member reports as untimed. Judgement counts come from different sources:
reconstructed from logs for two members and recorded during the runs for one.
The effort difference is therefore indicative, and time most of all.

## 9. Raw logs

Raw logs are stored per run as `docs/evaluation-runs/<member>/logs/case-NN-<method>.log`,
recorded with `script` during the measured runs; how each member's logs map to
their CSV rows, and any gaps, is documented in that member's `README.md`.
Reproducibility outputs are in `docs/evaluation-runs/reproducibility/`.

## 10. Threats to validity and protocol changes

- **Learning effect.** Within a case, whichever method runs second benefits
  from knowing the answer; the alternating, rotated order (Section 7)
  balances this but does not remove it. Effort is therefore also reported
  split by first/second position. All cases share one small project, so
  later cases are faster for either method.
- **Three-person sample of the tool's own authors.** All members know the
  tool and the case set; Chin Wen Hui authored the fixtures and ran a pilot
  before measurement, and Lu Wenxi checks the expected outcomes before
  measuring. Timing is indicative, not generalisable (proposal §5).
- **Controlled fixtures.** Three required files, one fault per case and one
  malformed-checklist variant. Manual judgements grow with the number of
  required files and status lines, so effort differences on larger real
  projects may differ from these results.
- **Procedure-defined counts.** Judgement points are defined by this protocol;
  the counts are only as fair as the lists in Sections 4.3 and 5. Checker
  counting is deliberately conservative.
- **Baseline blind spot.** `python3 -m zipfile -l` cannot show symlink or
  other file types; no fixture tests this, so the baseline is not penalised
  for it.
- **Tool version.** The pilot and all measured runs use checker commit
  `71d7472d7e920b2bba64327e9b69c3c18ecacd60` (Section 5.1). The results
  describe that version only; checker changes merged later are not covered
  and would need the affected cases to be re-run.

Protocol changes after this draft:

- 2026-11-04, before any measured run: quoted checker command paths; aligned
  judgement granularity (reviewer: Lu Wenxi).
- 2026-11-04, before any measured run: froze the assessed checker at commit
  `71d7472d7e920b2bba64327e9b69c3c18ecacd60` (Section 5.1); added the
  counting rationale to Section 4.4 (reviewer: Lu Wenxi).
- 2026-11-04, before any measured run: Section 8.6 reproducibility runs use
  the frozen checker commit on both GitLab CI and the unit server; the final
  submitted project is re-checked separately from a clean `git archive`
  extraction.
- 2026-11-06, after all measured runs: the §8.6 normalisation also replaces
  the exported checker directory with `<CHECKER>`, because case-05's error
  names the temporary checklist inside it and that directory differs between
  machines. The comparison was otherwise run as specified.
- 2026-11-06, after all measured runs: recorded the deviations found in review.
  Chin Wen Hui pasted the manual commands as one block, so the Section 4.3 stop
  rules did not take effect, and recorded three ERROR cases as FAIL under both
  methods (checker rows corrected from the logs in the derived file; manual rows
  kept as measured). Lu Wenxi corrected four durations after the runs. Yin Jiayu's
  first runs had no logs and were redone with `script`; ChatGPT assisted during
  timing in the redo, and three manual times exceed the gap to the next logged
  session. Chin Wen Hui's and Lu Wenxi's judgement counts were reconstructed from
  the logs under Sections 4.3 and 5; Yin Jiayu's were recorded during the runs.
  Lu Wenxi's corrected durations and all of Yin Jiayu's rows are
  flagged and excluded from the excluding-flagged-pairs view. Chin Wen Hui's
  deviations are disclosed but not flagged, so they remain in that view; a
  separate view without Chin Wen Hui is reported in Section 8.1.
- 2026-11-06: analysis uses `scripts/aggregate_eval.py`, which rejects incomplete,
  duplicate or out-of-range records instead of summarising them (reviewed in MR !17).
