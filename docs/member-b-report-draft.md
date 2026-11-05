# Member B report contribution draft

Author/owner: Yin Jiayu. Working text for team review, not a final report.

## 2. Tool design and rationale

Handoff Check assesses whether declared required regular files are present
in a selected Git commit and the ZIP being handed over. The checklist
provides project-specific requirements; Git status alone cannot determine
whether an untracked file is essential or irrelevant. The tool combines
these requirements with evidence from the working tree, selected commit
and archive, then reports the relevant differences.

Bash and Python have distinct responsibilities. Bash validates the
repository and CLI, resolves the selected ref once, retrieves the checklist
from that commit, captures NUL-delimited status/tree evidence, prepares the
archive, invokes Python and cleans up its temporary workspace. Python
validates the checklist and evidence, inspects regular-file types and ZIP
entries, applies the classification rules, and produces a readable report.
The interface passes six arguments with absolute file paths and a fixed
commit ID. Bash preserves the supported 0/1/2 checker exit codes.

The checker validates inputs before producing a verdict. Each checklist
entry must be a unique canonical relative path; invalid paths, malformed
JSON and ambiguous duplicate keys are rejected. Git evidence remains
NUL-delimited, including the two-path rename representation, so spaces and
newlines are not split into separate filenames. ZIP entries are inspected
without extraction and must match the declared path exactly. Duplicate,
unsafe or invalid archive entries produce ERROR rather than a potentially
misleading integrity verdict.

PASS means every required regular file exists in both selected commit and
ZIP. A missing file or unsupported type in either location produces FAIL.
Directories, symlinks and submodules cannot satisfy a regular-file
requirement. The report shows all three observed states and gives a reason
and suggested action for each failure. Working-tree evidence provides
context: a local CSV can explain why developer execution succeeds despite
its absence from the delivered commit. Unrelated untracked or ignored
files do not determine the verdict. Conversely, local absence alone does
not fail an otherwise complete selected-commit archive.

The implementation deliberately avoids rewriting ZIP paths or comparing
file contents. Exact paths make findings reproducible, while rejecting a
ZIP merely because it contains a top-level directory makes the supported
contract explicit. Required-file presence does not prove equal contents,
archive provenance or program correctness. Those require separate checks.
The checker also trusts the Bash evidence handoff and does not authenticate
arbitrarily supplied tree/status files.

The runtime uses the Python 3.12 standard library and needs no third-party
runtime packages. The current tests use unittest, allowing the existing
six interface test methods and 39 real-checker/helper methods to run
together without dependencies. The proposed pytest dependency was not
needed for this implementation; any later CI/test additions must be pinned
and documented by the team.

## 3. Technical limitations and current evidence

On 28 October 2026, all 32 local test methods passed using Python 3.12.14,
Bash 3.2.57 and Git 2.39.5 on macOS 15.7.4. The real checker produced PASS/0
for the complete handoff and FAIL/1 for the scenario with a locally present
CSV omitted from the selected commit and ZIP. The demo returned 0 because
both expected checker outcomes occurred. The evidence log identifies the
tested source and exact commands. These results support the tested local
behaviour; they do not establish measured efficiency improvements.

Chin Wen Hui independently reviewed the initial revision in MR !7 and
reproduced corrupt-DEFLATE exit-code handling and unrelated-name validation
defects. The follow-up catches archive stream failures as ERROR/2, preserves
raw context names, treats inaccessible working-tree paths as context, labels
input errors and reports the actual failing locations. Thirteen regression
methods were added; all 45 tests and both demos passed locally. Permission,
EOF and unexpected-error branches use fault injection, not universal
operating-system validation. Defensive duplicate/path policies are proposed
extensions awaiting team confirmation, not proposal requirements.

Re-review of the fixes, complete final unit-server reproduction, CI and
the agreed manual-baseline comparison remain to be completed. Member C
should add evaluation results; Member A should add final server evidence.

## 5. Traceable contribution

The Member B change introduces the Python checker, a sample checklist,
real-checker regression tests, a dependency-free test entry point and
design/verification notes. The implementation branch is
`feature-python-checker-jiayu`; the changes and peer review are in
[MR !7](https://git.infotech.monash.edu/fit2109/fit2109-s2-2026/group-assignment/MY-T06-06/-/merge_requests/7).
Earlier reviews of Member A's changes are retained in MR !1, !2, !3, !4,
!5 and !6 with their stated scopes. Chin Wen Hui must re-review the
follow-up revision before merge.
