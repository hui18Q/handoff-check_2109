# Handoff Check interface

## Purpose

Check whether declared required regular files are present in both a
selected Git commit and a handoff ZIP archive.

Working-tree evidence helps explain findings. PASS does not establish
file-content equality, archive provenance or program correctness.

## Public command

Run from the tool project root:

```bash
bash scripts/handoff_check.sh --repo PATH \
    [--ref REF] [--checklist PATH] [--zip PATH]
```

- `--repo`: required path to the root of a local, non-bare Git working
  repository. A subdirectory is rejected rather than silently checking
  its enclosing repository.
- `--ref`: target commit or ref; defaults to `HEAD`.
- `--checklist`: repository-relative checklist path; defaults to
  `handoff-check.json`.
- `--zip`: optional ZIP path, resolved from the caller's working directory.
- `--help`: print usage and exit successfully without checking a repository.

Resolve the target ref once to a commit ID. Use that same ID for all
selected-commit inspection and archive generation.

Read the checklist from the selected commit. This keeps its requirements
associated with the version being checked. Local checklist edits are not
used until committed and selected.

If no ZIP is supplied, create a temporary ZIP from the selected commit.
Check a supplied ZIP as provided; do not regenerate or modify it.

## Checklist

```json
{
  "required_files": [
    "README.md",
    "report.py",
    "data/items.csv"
  ]
}
```

The top-level value must be an object containing a non-empty
`required_files` array.

Each entry must be a non-empty string representing a canonical,
repository-relative file path using `/` separators. Reject absolute paths,
empty path components, `.` or `..` components, NUL characters and duplicate
entries.

Preserve filename case and spaces. Do not silently trim or rewrite paths.

The Python implementation additionally proposes a portable-checklist policy
that rejects literal backslashes and drive-like prefixes. This is not a
restriction on unrelated raw Git/ZIP names. Duplicate JSON keys and
duplicate/conflicting ZIP entries are rejected to avoid ambiguity; ZIP
absolute/traversal/empty-component/NUL paths are rejected as invalid input.
These defensive extensions remain subject to team confirmation in MR !7,
rather than being attributed to the proposal. See `docs/python-checker.md`.

## Bash responsibilities

- Validate command-line arguments and required commands.
- Validate the repository and resolve the target commit.
- Read the checklist from that commit.
- Collect Git status and selected-tree evidence.
- Generate an archive when none is supplied.
- Call the Python checker.
- Preserve the checker exit code and clean up temporary files.

Use NUL-delimited Git evidence so filenames containing spaces or newlines
are not split into separate records:

- Status: `git status --porcelain=v1 -z --untracked-files=all --ignored`
- Tree: `git ls-tree -r -z --full-tree COMMIT`

Keep the raw status and tree output in separate temporary files.

## Python interface and responsibilities

Proposed internal invocation:

```bash
python3 src/handoff_check.py \
    --repo REPOSITORY_ROOT \
    --commit COMMIT_ID \
    --checklist CHECKLIST_FILE \
    --status-file STATUS_FILE \
    --tree-file TREE_FILE \
    --archive ZIP_FILE
```

All internal file paths are absolute. `CHECKLIST_FILE` contains the
checklist obtained from the selected commit.

Bash also supplies the diagnostic-only `HANDOFF_CHECKLIST_SOURCE`
environment variable (`<checklist path> @ <ref>`) to Python. Checklist
errors report that source, not the temporary copy; the copy is still the
only checklist file read by Python. Direct invocations without this
variable label errors with the supplied file path.

Python validates the checklist, reads the supplied evidence, inspects
working-tree file types and ZIP entries, compares required paths, and
formats the findings.

Directory and symbolic-link entries do not satisfy a regular-file
requirement. ZIP paths must match repository-relative paths exactly;
automatic removal of a ZIP's top-level directory is outside this version.

## Results

| Result | Exit code | Meaning |
|---|---|---|
| PASS | 0 | Every required regular file is present in the selected commit and ZIP. |
| FAIL | 1 | A required regular file is absent or has an unsupported type in either location. |
| ERROR | 2 | Invalid input, unreadable or invalid archive, or a failed required command. |

Validate inputs before issuing a PASS or FAIL verdict. An ERROR prevents
a successful integrity verdict.

An unrelated untracked or ignored file must not independently cause FAIL
or ERROR. Parse status record structure, preserving names as supplied by Git
without applying checklist portability restrictions. Tree/ZIP names with
literal backslashes or drive-like prefixes are also preserved for exact
matching; unrelated such entries must not end the assessment.
Working-tree absence alone must not cause FAIL when the selected commit
and archive both satisfy the requirement. If local file-type inspection
raises an I/O or permission error, report `inaccessible` as context.

The report identifies the selected commit and provides per-file evidence
for the working tree, selected commit and archive. Each FAIL finding
includes its reason and a suggested next action.
Each reason names the actual failing location(s) and state, rather than
blaming both locations when only one is missing or unsupported. Unrelated
status paths are listed with escaped names and status codes as context.

Write completed assessment reports to standard output. Write operational
and invalid-input errors to standard error.
Input errors name the affected source/path, with checklist indices or JSON
line/column where available. Invalid compressed streams, CRC failures and
truncated archives produce ERROR/2 without a completed PASS/FAIL verdict.

## Safety and reproducibility

Do not stage, commit, switch branches, remove files or modify configuration
in the target repository.

Keep generated files in a dedicated temporary workspace inside the tool
project. Clean up that workspace after success or failure.

Use Bash and Python 3.12. The runtime uses Python standard-library modules.
Demonstration fixtures must be rebuildable offline from submitted files
without depending on the tool repository's existing Git history.

## Bash integration status — 26 October 2026

The Bash workflow now invokes `src/handoff_check.py` using the six internal
arguments documented above. The Python executable is `python3` from PATH
and must be Python 3.12. Activate the project's Python 3.12 virtual
environment before running an assessment.

Help remains available without the checker. A missing or unreadable
checker produces ERROR with exit code 2.

Completed assessment output is supplied by Python. Bash forwards the
checker's standard output and standard error, and preserves exit codes
0, 1 and 2 when cleanup succeeds. An unsupported checker exit code or
cleanup failure produces ERROR with exit code 2.

The isolated interface tests can be run with:

```bash
python3 tests/test_bash_python_interface.py -v
```

These tests create temporary Git fixtures and a temporary tool copy with
a Python test double. They check argument delivery, selected-commit
evidence, exit codes, output streams, archive handling and cleanup.

The real Python checker's classification and diagnostic behaviour still
require integration testing. Passing these interface tests does not
establish the completed checker's correctness or measured improvement.
