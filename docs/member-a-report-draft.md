Member A — Report Contribution Draft

Author: Lu Wenxi
Status: Working draft for integration into the final group report

Scenario and Problem

A Git-based project handoff can omit a required runtime input even when the program runs successfully in the developer’s working directory. The developer may retain an untracked or ignored file that is absent from the selected commit and its exported archive. The receiver consequently obtains a package that cannot reproduce the developer’s execution.

Our controlled inventory-report scenario demonstrates this mechanism. The program reads data/items.csv, counts its records and sums the quantity column. With the submitted input, it reports three records and a total quantity of ten.

The scenario compares a complete handoff with one that omits the required CSV. The omission is intentionally introduced to make the failure reproducible. This experiment demonstrates the failure mechanism rather than documenting an accidentally observed production incident.

The scenario motivates a specific assessment: determine whether declared required regular files exist in both the selected Git commit and the handoff ZIP. Working-tree evidence helps explain why the developer may still possess a file that the receiver will not obtain.

The assessment is limited to declared required-file presence. It does not establish file-content equality, archive provenance or successful execution of the handed-over program.

Bash Workflow Contribution

The Bash entry point accepts a repository root, an optional target ref, a repository-relative checklist path and an optional supplied ZIP.

It validates the arguments and repository, then resolves the requested ref once to a commit ID. Subsequent checklist retrieval, selected-tree inspection and generated archive creation use that same commit ID. This keeps the assessment associated with one selected version.

The checklist is read from the selected commit rather than from a locally edited copy. Requirements are therefore associated with the version being assessed, and uncommitted checklist changes do not silently alter the assessment.

Bash collects working-tree status and selected-tree evidence in separate temporary files. The Git commands use NUL-delimited output so filenames containing spaces or newlines are not split into separate records. Optional Git locking is disabled for status collection to avoid an incidental index refresh.

A supplied archive is checked as provided. Otherwise, Bash creates a temporary ZIP from the selected commit. It invokes the Python checker with the resolved commit ID and absolute paths to the repository, committed checklist, status evidence, tree evidence and archive.

Python is responsible for checklist and archive validation, required-file assessment and findings. Bash forwards the checker’s output and preserves its supported exit codes: zero for PASS, one for FAIL and two for ERROR. Unsupported checker exit codes produce ERROR.

Temporary workspaces have exit and signal cleanup handlers. The exercised interface tests cover cleanup in selected cases; signal handling and cleanup-failure behaviour require additional verification.

Rebuildable Demonstration

The demonstration script is designed to copy the submitted inventory files into a temporary Git repository and create two commits.

The first commit includes the README, program, checklist and required CSV. The second removes the CSV from tracking and adds an ignore rule while retaining the CSV in the working directory. This models a developer possessing a runtime input that is absent from the handed-over version.

Both assessments select explicit commit IDs. The complete commit is assessed after the missing-file commit has been created, so the normal case also exercises selection of an earlier commit rather than the fixture’s current HEAD.

The intended checker outcomes are exit code zero for the complete commit and exit code one for the missing-file commit. The demonstration itself should return zero only when both checker exit codes match their expected outcomes.

The fixtures are constructed from submitted files without network access or reliance on the tool repository’s existing Git history. They are placed in a temporary workspace with cleanup on exit.

At the time of this draft, fixture construction and complete assessments through the demonstration script have not been exercised with the real Python checker.

Verification Completed

The inventory program executed successfully under Python 3.12.16 and reported three records with a total quantity of ten.

Six isolated Bash/Python interface test methods passed locally. These tests use a controlled Python test double to exercise argument and evidence delivery, output streams, supported exit codes, supplied archive handling and preservation, cleanup, and selected operational errors.

A clean extraction of commit 917960b initially contained neither Git history nor an existing virtual environment. A new Python 3.12.16 virtual environment was created inside that extraction. The inventory example and all six isolated interface test methods passed.

The clean-extraction run used macOS, Bash 3.2.57 and Git 2.50.1. The recorded interpreter path confirmed that the commands used the extracted project’s new virtual environment.

Demonstration syntax validation passed. With the real checker absent, demonstration prerequisite validation reported the missing checker and returned exit code two. This validates the exercised prerequisite failure rather than a successful end-to-end demonstration.

These results provide evidence for the recorded local setup, example execution and isolated interface behaviour. They do not establish the real checker’s classification or diagnostic correctness, complete demonstration behaviour, or execution on the unit server.

Evidence Sources

The scenario and its reproduction procedure are documented in docs/scenario.md.

The local interface-test run is recorded in docs/evidence/bash-python-interface-2026-10-26.txt.

Demonstration syntax and missing-checker preflight results are recorded in docs/evidence/demo-preflight-2026-10-27.txt.

The local clean-extraction run is recorded in docs/evidence/clean-extraction-preflight-2026-10-27.txt.

AI assistance, human verification, review status and remaining risks are recorded in docs/ai-use.md.

Remaining Work Before Finalisation

The real Python checker must be integrated and assessed against normal, missing-file and invalid-input cases. Both demonstration cases must then execute successfully with their expected checker outcomes, and cleanup after fixture creation must be verified.

The documented setup and complete workflow must also be reproduced on the unit server from a clean extraction. Independent review findings must identify the reviewed commits and distinguish completed checks from remaining limitations.

The final report must incorporate the team’s completed automated testing and CI evidence, together with the author’s results from the agreed manual-baseline comparison. Claims about correctness, diagnostic usefulness or workflow improvement must be supported by those results.

No measured workflow improvement is claimed in this draft.
