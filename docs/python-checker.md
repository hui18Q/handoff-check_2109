# Python checker: contract and review notes

Owner: Yin Jiayu. Independent checker: Chin Wen Hui.
MR !7 was reviewed at `77dc8fa63136d092ce4eee1cefc2b76271664119`;
the follow-up revision requires re-review before merge.

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
   records the destination precedes the source. Parse both records, preserving
   literal status names rather than validating them as checklist paths.
4. Inspect exact archive entry paths without extraction or prefix removal.
   Validate the ZIP, including CRC checks, before reporting PASS or FAIL.
5. A required path passes only when it names a regular file in both the
   selected tree and ZIP. Missing or unsupported types produce FAIL/1.
   Git regular/executable blob modes count as regular files; symlinks,
   directories and submodules do not. ZIP symlinks and special files do
   not count as regular files.
6. Working-tree state and unrelated status paths explain findings but
   do not independently cause FAIL or ERROR. A locally missing file may still pass
   if both selected commit and ZIP contain it. Local symlink ancestors
   are reported without following them to inspect an external path. A local
   inspection failure reports `inaccessible`; it does not block assessment
   from otherwise valid commit and archive evidence.
7. Print per-file evidence and a suggested next action for each failure.
   PASS uses exit 0, FAIL exit 1, invalid input/operational ERROR exit 2.

## Proposal rules versus defensive extensions

The proposal-derived outcomes are presence-based PASS/0 or FAIL/1, invalid
input ERROR/2, and context-only local/status evidence. Tests of those rules
assert the verdict and relevant evidence, not a particular full sentence.

The following are implementation policies proposed for team confirmation,
not extra requirements claimed to come from the proposal:

- Checklist names use portable `/`-separated paths, excluding literal
  backslashes and drive-like prefixes such as `C:`. This restriction is
  **only for declared checklist requirements**. Raw tree/ZIP entries may
  contain these names; unrelated entries do not invalidate the assessment.
- Duplicate JSON object keys, duplicate checklist requirements and
  duplicate/conflicting ZIP entries produce ERROR instead of silently
  choosing an interpretation. Errors identify duplicate checklist indices
  or the ambiguous key/entry where available.
- ZIP entry names containing NUL, absolute paths, `.`/`..` or empty path
  components produce ERROR. Archives are never extracted. This is a
  conservative invalid-input policy, not a claim of content/provenance
  checking or comprehensive ZIP security validation.

Chin Wen Hui raised the policy distinction in S5. These extension tests
document the current implementation; they do not establish team acceptance.
The reviewer/team should confirm or request changes before merge.

Errors from each input reader name the source (Checklist, Tree evidence,
Status evidence or ZIP archive) and its path. Checklist schema errors
include the `required_files[index]`; malformed JSON retains its line and
column. The public command labels errors with the requested checklist
path and ref; the checker still reads the committed copy supplied by Bash,
not an uncommitted working-tree edit. Invalid DEFLATE/CRC/truncated archives
return ERROR/2 without a traceback or completed verdict. Unexpected
internal exceptions also return ERROR/2 rather than masquerading as FAIL/1.

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

The first runs both the six existing interface tests and 39 real
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

The review regressions include a genuinely corrupted DEFLATE stream through
the public Bash entry point, raw untracked/ignored/renamed and tracked names
with backslashes or drive-like prefixes, input-labelled diagnostics and
location-specific failure reasons. Permission/I/O, EOF and unexpected-error
branches are fault-injected with `unittest.mock`; these are not claims of
real permission-denied execution on every operating system.

The standard-library test runner keeps setup dependency-free and runs
the existing unittest-based interface suite together with new tests.
This differs from the proposal's planned pytest dependency. Member C can
integrate these tests into the final test/CI workflow; any added package
must be pinned and justified. CI and baseline evaluation are not claimed
complete by this change.

Chin Wen Hui should re-review the revised rules and expected outcomes, then
reproduce both commands from this branch before approval. Final complete
unit-server verification remains with the team after integration.
