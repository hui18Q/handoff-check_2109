# Python checker: contract and review notes

Owner: Yin Jiayu. Independent checker: Wen Chin (review pending).

The implementation is `src/handoff_check.py`. The public Bash script
provides exactly six internal arguments:

```text
--repo ABSOLUTE_REPO_ROOT
--commit FULL_COMMIT_ID
--checklist ABSOLUTE_COMMITTED_CHECKLIST_COPY
--status-file ABSOLUTE_PORCELAIN_V1_Z_FILE
--tree-file ABSOLUTE_LS_TREE_Z_FILE
--archive ABSOLUTE_ZIP_PATH
```

## Decision rules

1. Validate the internal inputs before issuing any assessment verdict.
2. Read a JSON object with a non-empty `required_files` array. Require
   unique canonical repository-relative string paths. Reject absolute,
   drive-qualified, traversal, empty-component, backslash-separated and
   NUL-containing paths. Preserve case, spaces and newlines.
3. Parse raw NUL-delimited Git evidence. In porcelain-v1 `-z` rename/copy
   records the destination precedes the source. Parse both records.
4. Inspect exact archive entry paths without extraction or prefix removal.
   Validate the ZIP, including CRC checks, before reporting PASS or FAIL.
5. A required path passes only when it names a regular file in both the
   selected tree and ZIP. Missing or unsupported types produce FAIL/1.
   Git regular/executable blob modes count as regular files; symlinks,
   directories and submodules do not. ZIP symlinks and special files do
   not count as regular files.
6. Working-tree state and unrelated status paths explain findings but
   do not independently cause FAIL. A locally missing file may still pass
   if both selected commit and ZIP contain it. Local symlink ancestors
   are reported without following them to inspect an external path.
7. Print per-file evidence and a suggested next action for each failure.
   PASS uses exit 0, FAIL exit 1, invalid input/operational ERROR exit 2.

Duplicate JSON object keys, duplicate/conflicting ZIP entries and unsafe
ZIP paths are treated as invalid input (ERROR), rather than silently
choosing one interpretation. This conservative policy is explicit so
reviewers can check the expected outcomes independently.

## Scope and alternatives

The selected commit, not a local checklist edit, determines requirements.
The Bash side supplies that committed version. The checker trusts this
internal evidence handoff; independently supplied evidence is not proof
that a tree belongs to a claimed commit.

Blanket failure for any untracked file was rejected because unrelated
notes and caches need not affect handoff completeness. Automatically
removing a ZIP prefix was rejected because it changes the exact-path
contract. Content hashes and archive provenance are outside this version;
a same-named file with different contents can still pass a presence check.

The runtime uses only the Python 3.12 standard library. `json` parses the
checklist, `zipfile` reads archives, `pathlib`/`stat` inspect file types,
and `argparse` implements the internal CLI. No external command is invoked
by Python; Bash retains repository/ref validation, Git evidence capture,
archive creation and temporary-workspace cleanup.

## Reproduction

Activate Python 3.12 and run:

```bash
bash scripts/test.sh
bash scripts/demo.sh
```

The first runs both the six existing interface tests and 26 new real
checker/helper tests. The second uses the real checker for a complete
selected commit and a commit omitting the required CSV while retaining
it locally. Expected checker exits are 0 and 1; expected demo exit is 0.

The added tests include export-ignore, unrelated ignored/untracked files,
selected-commit checklist retrieval, missing local files, supplied ZIP
paths/preservation, top-level ZIP prefixes, case, whitespace/newline names,
renames, symlinks, directories, special files, malformed/duplicate JSON,
invalid paths, malformed Git evidence, duplicate ZIP entries, corrupt ZIPs,
CRC errors and missing inputs. Target-repository preservation and temporary
cleanup are checked around the real Bash-to-Python assessments.

The standard-library test runner keeps setup dependency-free and runs
the existing unittest-based interface suite together with new tests.
This differs from the proposal's planned pytest dependency. Member C can
integrate these tests into the final test/CI workflow; any added package
must be pinned and justified. CI and baseline evaluation are not claimed
complete by this change.

Wen Chin should review the decision rules and expected outcomes, then
reproduce both commands from this branch before approval. Final complete
unit-server verification remains with the team after integration.
