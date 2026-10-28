## Discover — controlled handoff scenario investigation

- Dates: 12–13 October 2026.
- Owner: Lu Wenxi.
- Checker: Yin Jiayu.
- AI tool: OpenAI ChatGPT, https://chatgpt.com/.
- Task and instructions: Explain how to construct and document a reproducible Git handoff scenario, including a normal archive and a required CSV that exists locally but is absent from the selected commit.
- AI output: Suggested inventory-report files, Git and archive commands, reproduction instructions, and evidence-recording steps.
- Human verification: Lu Wenxi executed the commands, inspected Git status, commit file lists and ZIP contents, and ran the developer and receiver copies. Normal receivers exited with code 0; fault receivers raised FileNotFoundError and exited with code 1.
- Decision: The suggested approach was used for the local controlled reproduction.
- Evidence: docs/scenario.md and the three logs in docs/evidence/.
- Remaining limitations: The experiment intentionally introduces the omission. It establishes the failure mechanism but does not establish the completed checker's correctness or measured workflow improvement. Python 3.12 validation and investigation of the real workflow need remain pending.

AI assistance with drafting the proposal is acknowledged separately in its Appendix D.

## Design — Bash and Python interface draft

- Date: 24 October 2026.
- Owner: Lu Wenxi.
- Checker: Yin Jiayu (independent review pending).
- AI tool: OpenAI ChatGPT, https://chatgpt.com/.
- Task and instructions: Help define a reviewable interface between the Bash workflow and Python checker, consistent with the submitted proposal.
- AI output: A draft covering CLI arguments, checklist source, Git evidence files, Python invocation, verdicts, exit codes and temporary-file handling.
- Requirements retained from the proposal: Bash collects Git evidence and manages archives; Python validates and compares required files; PASS, FAIL and ERROR use exit codes 0, 1 and 2.
- Proposed details requiring team review: Reading the checklist from the selected commit, canonical checklist paths, exact ZIP path matching, and the internal Python arguments.
- Human verification completed: The draft was saved and displayed for inspection. No implementation tests or independent interface review have been completed for this activity.
- Planned independent checks: Yin Jiayu will compare the draft with the proposal and Python design, walk through normal, missing-file and invalid-input cases, and record any required changes.
- Status: Draft awaiting independent review.
- Decision: Pending. An Accepted, Modified or Rejected decision will be recorded with supporting evidence after review.
- Evidence: docs/handoff-interface.md.
- Remaining risks: The proposed interface may require changes during review and integration. Filename handling, archive validation and command failures still require executable tests.

## Build — Bash CLI scaffold and argument validation

- Date: 24 October 2026.
- Owner: Lu Wenxi.
- Checker: Yin Jiayu (independent review pending).
- AI tool: OpenAI ChatGPT, https://chatgpt.com/.
- Task and instructions: Draft the Bash help and argument-parsing layer using the proposed interface. Handle invalid arguments with exit code 2.
- AI output: A Bash scaffold containing help text, default values, option parsing and argument-validation functions.
- Human-led responsibilities: Confirm the required behaviour, inspect the saved script, execute checks, interpret results and decide whether the implementation is ready for integration.
- Human verification: Lu Wenxi ran the syntax check and CLI commands below on macOS. The latest saved version produced the expected results.
- Debugging observation: Earlier runs produced unexpected empty output and exit code 0. After inspecting the saved file, the checks were repeated successfully. The original cause was not established.
- Evidence: scripts/handoff_check.sh and the manual verification results below.
- Status: CLI scaffold verified locally; independent review pending.
- Decision: Pending independent review. Record the final Accepted, Modified or Rejected decision and review evidence before merging.
- Remaining limitations: Repository validation, Git evidence collection, archive handling and Python integration are not implemented. Valid CLI input currently reaches an explicit ERROR placeholder. This is not an end-to-end tool validation.

| Check | Observed result |
|---|---|
| `bash -n scripts/handoff_check.sh` | No syntax error; exit 0 |
| `--help` | Help displayed; exit 0 |
| No arguments | Missing required `--repo`; exit 2 |
| `--repo` | Missing value; exit 2 |
| `--repo --ref HEAD` | Option used instead of a value; exit 2 |
| `--repo ""` | Empty value rejected; exit 2 |
| `--repo .` | Explicit development placeholder; exit 2 |

## Build — Repository validation and commit resolution

- Date: 24 October 2026.
- Owner: Lu Wenxi.
- Checker: Yin Jiayu (independent review pending).
- AI tool: OpenAI ChatGPT, https://chatgpt.com/.
- Task and instructions: Extend the Bash CLI to validate a local Git working repository and resolve the requested ref to a fixed commit ID.
- AI output: Proposed repository-validation and commit-resolution functions, a root-directory restriction, and manual verification commands.
- Human verification: Lu Wenxi saved and inspected the implementation and executed the following checks on macOS. These checks exercised uncommitted working-tree changes on feature-handoff-bash.

| Check | Observed result | Exit code |
|---|---|---|
| Current repository root with default HEAD | Printed the absolute repository root and selected commit; reached the explicit development placeholder | 2 |
| Nonexistent ref | Reported that the ref could not resolve to an available commit | 2 |
| Script file supplied as repository path | Rejected the path because it was not a directory | 2 |
| Repository subdirectory supplied as repository path | Rejected the path because the repository root was required | 2 |

- Commit cross-check: The selected commit was 63cb487766789d959085db72e4acec53d9639bf2, matching the separate git rev-parse HEAD output.
- Proposed interface detail: --repo must identify the repository root. The help text and docs/handoff-interface.md document this restriction.
- Status: The listed local checks passed; independent review is pending.
- Decision: Pending independent review and any resulting changes.
- Evidence: scripts/handoff_check.sh, docs/handoff-interface.md, and the manual observations recorded above.
- Remaining limitations: Checklist retrieval, Git evidence collection, archive handling, Python integration, automated regression tests and Python 3.12 unit-server verification are not yet complete. These checks do not establish the completed checker's correctness.
## Build — Temporary workspace and exit cleanup

- Date: 24 October 2026.
- Owner: Lu Wenxi.
- Checker: Yin Jiayu (independent review pending).
- AI tool: OpenAI ChatGPT, https://chatgpt.com/.
- Task and instructions: Add a dedicated temporary workspace inside the tool project and clean it up when the Bash workflow exits.
- AI output: Proposed workspace initialization, an EXIT cleanup function, signal handlers, and manual verification commands.
- Human verification: Lu Wenxi saved the implementation and ran the following checks on macOS against uncommitted working-tree changes.

| Check | Observed result | Exit code |
|---|---|---|
| Bash syntax check | No syntax errors reported | 0 |
| Valid repository invocation | Created a temporary directory inside the tool project and reached the explicit development placeholder | 2 |
| Post-exit directory check | No temporary workspace remained | 0 |
| CLI help regression check | Displayed the usage information | 0 |

- Exit-code observation: Cleanup preserved the development placeholder's exit code of 2.
- Status: The listed local checks passed; independent review is pending.
- Decision: Pending independent review and any resulting changes.
- Evidence: scripts/handoff_check.sh and the manual observations recorded above.
- Remaining limitations: Signal handling, cleanup after exit codes 0 and 1, and cleanup failure have not yet been verified on the owner's Mac. Checklist retrieval, Git evidence collection, archive handling, Python integration and Python 3.12 unit-server verification remain incomplete.

## Build — Committed checklist retrieval and Git evidence collection

- Date: 24 October 2026.
- Owner: Lu Wenxi.
- Checker: Yin Jiayu (independent review pending).
- AI tool: OpenAI ChatGPT, https://chatgpt.com/.
- Task and instructions: Read the checklist from the selected commit, reject non-canonical checklist paths, and collect raw NUL-delimited Git status and tree evidence.
- AI output: Proposed path validation, committed-blob retrieval, separate evidence files, and controlled manual verification steps.
- Human verification: Lu Wenxi inspected the implementation and ran the following checks on macOS against uncommitted working-tree changes.

| Check | Observed result | Exit code |
|---|---|---|
| Bash syntax | No syntax errors reported | 0 |
| CLI help | Usage information displayed | 0 |
| Committed checklist present | Checklist and Git evidence collection completed before the development placeholder | 2 |
| Checklist absent from selected commit | Reported that the checklist could not be read | 2 |
| Checklist path containing .. | Rejected the path | 2 |
| Local checklist differs from committed checklist | Execution trace showed retrieval from the fixed commit rather than the local file; reached the development placeholder | 2 |
| Post-exit temporary-directory check | No temporary workspace remained | 0 |

- Fixture: A separate temporary Git repository was created under .scenario-runs. Its recorded commit was 379cf2236e8dfd73d855ac043bd7c074e4068d88. This fixture commit is not a development commit in the tool repository.
- Source cross-check: The committed checklist required README.md; the uncommitted local checklist required LOCAL_ONLY_DO_NOT_USE.txt. The trace showed cat-file reading 379cf2236e8dfd73d855ac043bd7c074e4068d88:handoff-check.json.
- Evidence-command inspection: The trace showed status --porcelain=v1 -z --untracked-files=all --ignored and ls-tree -r -z --full-tree using the selected commit. It also showed removal of the tool's temporary workspace.
- Status: The listed local checks passed; independent review is pending.
- Decision: Pending independent review and any resulting changes.
- Evidence: scripts/handoff_check.sh and docs/evidence/bash-evidence-trace-2026-10-24.txt.
- Remaining limitations: The owner's checks inspected the commands and their outcomes; they did not independently compare the raw evidence bytes or test unusual filenames. JSON content validation, archive handling, Python integration, complete target-repository preservation checks and Python 3.12 unit-server verification remain incomplete.

## Build — Generated and supplied ZIP handling

- Date: 24 October 2026.
- Owner: Lu Wenxi.
- Checker: Yin Jiayu (independent review pending).
- AI tool: OpenAI ChatGPT, https://chatgpt.com/.
- Task and instructions: Support an existing ZIP resolved from the caller's working directory, or generate a temporary ZIP from the fixed selected commit.
- AI output: Proposed archive preparation, readable-file checks, source reporting, and manual verification steps.
- Human verification: Lu Wenxi inspected the implementation and executed the following checks on macOS against uncommitted working-tree changes.

| Check | Observed result | Exit code |
|---|---|---|
| Bash syntax | No syntax errors reported | 0 |
| CLI help | Usage information displayed | 0 |
| Automatic ZIP generation | Used the fixed selected commit and reached the Python development placeholder | 2 |
| Supplied ZIP using an absolute path | Selected the supplied archive and reached the Python development placeholder | 2 |
| Supplied ZIP using a relative path | Resolved the archive from the caller's working directory and reached the Python development placeholder | 2 |
| Supplied ZIP filename containing spaces | Preserved the complete filename in both supplied-path checks | 2 |
| Nonexistent supplied ZIP | Reported that the supplied ZIP was not a readable file | 2 |

- Selected-commit observation: The generation trace used commit 379cf2236e8dfd73d855ac043bd7c074e4068d88, matching the reported selected commit.
- Supplied-file content check: SHA-256 before and after both supplied-ZIP invocations was c84204106090eb709a8803241f4faa18217449b970aaabe4a71a22b25fa4642b.
- Cleanup observation: The automatic-generation trace showed removal of the dedicated temporary workspace after the development placeholder returned 2.
- Status: The listed local checks passed; independent review is pending.
- Decision: Pending independent review and any resulting changes.
- Evidence: scripts/handoff_check.sh and docs/evidence/bash-archive-trace-2026-10-24.txt.
- Remaining limitations: These owner checks did not inspect the generated ZIP's entries or exercise archive-generation failure. ZIP validity, required-file assessment, Python integration, complete target-repository preservation checks and Python 3.12 unit-server verification remain incomplete.

## Review follow-up — Interface, CLI and Git evidence

- Recorded date: 26 October 2026.
- Owner: Lu Wenxi.
- Independent checker: Yin Jiayu.
- Review date: 24 October 2026, as stated in the review comment.
- Reviewed implementation: 24b2d5e, including the original CLI commit 63cb487.
- Reviewer-reported environment: macOS 15.7.4, Bash 3.2.57, Git 2.39.5 and Python 3.14.2 for the review harness only.
- Reviewer-reported results: 59/59 local assertions passed.
- Reviewed scope: Proposed interface responsibilities, CLI validation, repository/ref validation, checklist-path rejection, committed checklist retrieval, NUL-delimited Git status/tree evidence and cleanup in the exercised cases.
- Evidence findings: The reviewer reported byte-for-byte agreement with separate Git commands, including a newline-containing filename and a staged rename with spaces. The fixture's file contents, index, refs and configuration remained unchanged.
- Independent conclusion: No blocking issue was found in the implemented subset.
- Owner decision: Accepted for the reviewed subset, based on the independent findings. The proposed Python invocation remains subject to integration testing.
- Status update: This follow-up resolves the earlier pending-review status for the scope reviewed at 24b2d5e. Earlier activity entries preserve their original development-stage observations.
- Scope boundary: This review does not cover ZIP handling introduced in e56c5e8 or the later virtual-environment ignore rule in 79be3eb. Supplementary review of the current branch remains pending.
- Remaining limitations: Completed PASS/FAIL assessment, Python integration, Python 3.12 unit-server verification, signal/cleanup-failure handling and measured workflow improvement remain unvalidated by this review.
- Evidence: Yin Jiayu's review comment in MR !3, https://git.infotech.monash.edu/fit2109/fit2109-s2-2026/group-assignment/MY-T06-06/-/merge_requests/3.

## Review follow-up — Bash archive preparation

- Date: 28 October 2026.
- Owner: Lu Wenxi.
- Independent checker: Yin Jiayu.
- Reviewed version: 39021040cb486b8d754840aaa87945a3eb25ed8f, including ZIP implementation e56c5e83.
- Reviewer-reported environment: macOS 15.7.4, Bash 3.2.57, Git 2.39.5 and Python 3.12.14 for the review harness.
- Reviewer-reported results: All nine additional checks passed. Generated archives used the fixed selected commit. Absolute and caller-relative supplied ZIP paths, including spaces, worked. Supplied ZIP bytes, permissions and modification times remained unchanged. Missing ZIP and injected archive-command failure returned 2. Temporary workspaces were removed, and the exercised target-repository state remained unchanged.
- Additional inspection: The reviewer checked the virtual-environment ignore rule and updated documentation.
- Independent conclusion: No blocking issue was found in the Bash preparation stage; it is acceptable for stage-specific integration after recording this review.
- Owner decision: Accepted for the reviewed Bash preparation scope, based on the independent findings.
- Status update: This supplements the earlier review of 24b2d5e and resolves the pending supplementary review for the changes inspected at 3902104.
- Evidence: Yin Jiayu's supplementary ZIP review dated 28 October 2026 in MR !3.
- Remaining limitations: This acceptance does not establish real Python classification, complete end-to-end assessment, full unit-server workflow verification, signal handling or cleanup-failure behaviour. The development-placeholder exit code 2 is not PASS.

## Build — Bash invocation of the Python checker

- Date: 26 October 2026.
- Owner: Lu Wenxi.
- Checker: Yin Jiayu (independent review pending).
- AI tool: OpenAI ChatGPT, https://chatgpt.com/.
- Task and instructions: Connect the existing Bash preparation workflow to the proposed Python interface, preserve its supported exit codes and retain temporary-workspace cleanup.
- AI output: A complete revised Bash script containing Python 3.12 validation, checker-file validation, the six-argument invocation and exit-code handling.
- Contract: Inputs and PASS/FAIL/ERROR meanings follow the proposal and docs/handoff-interface.md. Python remains responsible for checklist validation, file assessment and findings.
- Human verification: Lu Wenxi saved the script, ran Bash syntax and help checks, confirmed the missing-checker error returned 2, and confirmed no temporary workspace remained. The isolated interface tests subsequently passed under Python 3.12.16.
- Status: Locally verified for the recorded scope; independent review and real-checker integration are pending.
- Decision: Pending independent review and any resulting changes.
- Evidence: scripts/handoff_check.sh and docs/evidence/bash-python-interface-2026-10-26.txt.
- Remaining risks: The real Python implementation has not been exercised through this invocation. Complete assessment behaviour, unit-server execution and additional failure handling require verification.

## Verify — Isolated Bash and Python interface tests

- Date: 26 October 2026.
- Owner: Lu Wenxi.
- Checker: Yin Jiayu (independent review pending).
- AI tool: OpenAI ChatGPT, https://chatgpt.com/.
- Task and instructions: Verify Bash orchestration while keeping the real Python checker separate from an isolated test double.
- AI output: A standard-library unittest suite that creates temporary tool copies, Git repositories, archives and a controlled Python interface double.
- Expected behaviour: Preserve supported checker exit codes and output streams; use the selected commit's checklist and tree; preserve raw NUL-delimited evidence; resolve supplied ZIP paths correctly; preserve target files and supplied ZIPs; clean temporary workspaces; report operational errors with exit code 2.
- Human verification: Lu Wenxi saved and executed the suite on macOS using Python 3.12.16, Bash 3.2.57(1)-release and Git 2.50.1. All six test methods passed and the test process exited with code 0.
- Tested cases: Supported exit codes 0/1/2 and evidence delivery; supplied ZIP paths and preservation; missing checker; unsupported checker exit; missing supplied ZIP; invalid ref.
- Reproduction: Run python3 tests/test_bash_python_interface.py -v from the project root. Fixtures are constructed from submitted code without requiring the tool repository's existing Git history.
- Source state: The recorded run exercised uncommitted changes on feature-handoff-python-integration based on commit 39021040cb486b8d754840aaa87945a3eb25ed8f.
- Status: Local interface tests passed; independent review is pending.
- Decision: Pending independent review and any resulting changes.
- Evidence: tests/test_bash_python_interface.py and docs/evidence/bash-python-interface-2026-10-26.txt.
- Remaining risks: The test double does not implement required-file classification or diagnostics. These results do not validate the real checker, the complete pytest/CI workflow, unit-server execution or improvement over the manual baseline.

## Review follow-up — Bash and Python invocation interface

- Date: 28 October 2026.
- Owner: Lu Wenxi.
- Independent checker: Yin Jiayu.
- Reviewed version: c8cf660661e3cfece3b856707e5110de4dcbe495.
- Reviewer-reported environment: macOS 15.7.4, Bash 3.2.57, Git 2.39.5 and Python 3.12.14, using a separate checkout.
- Reviewer-reported results: Syntax and help checks returned 0. All six interface test methods passed and the test process returned 0. The reviewer checked the implementation and test expectations against the documented interface.
- Reviewed scope: Six internal arguments, selected-commit checklist/tree/archive evidence, NUL-delimited evidence, supported exit-code and output-stream forwarding, unsupported exit handling, supplied ZIP preservation, exercised operational errors, cleanup and target-repository preservation.
- Independent conclusion: The Bash-to-Python interface changes are acceptable for stage-specific integration; no code change was required in the exercised scope.
- Owner decision: Accepted for the reviewed interface scope, based on the independent findings.
- Status update: This resolves the pending independent review of the Build and Verify interface activities at c8cf660.
- Integration handling: The append-only AI-use conflict was resolved with AI assistance, retaining both branches' records.
- Evidence: Yin Jiayu's interface review dated 28 October 2026 in MR !4, https://git.infotech.monash.edu/fit2109/fit2109-s2-2026/group-assignment/MY-T06-06/-/merge_requests/4.
- Remaining limitations: These tests use a controlled Python test double. Real-checker classification and diagnostics, a complete end-to-end demonstration and final unit-server workflow verification remain outside this acceptance.
