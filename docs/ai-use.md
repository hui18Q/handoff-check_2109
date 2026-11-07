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

## Build — Rebuildable inventory handoff demonstration

- Date: 27 October 2026.
- Owner: Lu Wenxi.
- Checker: Yin Jiayu (independent review pending).
- AI tool: OpenAI ChatGPT, https://chatgpt.com/.
- Task and instructions: Draft an end-to-end demonstration that rebuilds normal and missing-file inventory scenarios from submitted files without relying on existing Git history.
- AI output: scripts/demo.sh, including prerequisite checks, temporary fixture construction, two selected commits, checker invocation, expected exit-code checks and cleanup.
- Intended behaviour: The complete selected commit should produce checker exit code 0. The commit omitting the required CSV should produce checker exit code 1 while retaining the CSV locally. The demonstration should exit with 0 only when both expected outcomes occur.
- Human verification: Lu Wenxi saved the script and ran it using Python 3.12.16. Bash syntax validation returned 0. With the real Python checker absent, the script reported the missing checker and returned 2.
- Verification boundary: Execution stopped during prerequisite validation. Fixture construction, both checker assessments and cleanup after fixture creation were not exercised by this run.
- Status: Syntax and missing-checker preflight checked locally; complete demonstration and independent review are pending.
- Decision: Pending independent review and executable end-to-end verification.
- Evidence: scripts/demo.sh and docs/evidence/demo-preflight-2026-10-27.txt.
- Remaining risks: The demonstration must be checked with the real Python implementation, coordinated with the team's fixture conventions, and verified from a clean extraction on the unit server.

## Build — Development README and reproduction instructions

- Date: 27 October 2026.
- Owner: Lu Wenxi.
- Checker: Yin Jiayu (independent review pending).
- AI tool: OpenAI ChatGPT, https://chatgpt.com/.
- Task and instructions: Draft English setup, demonstration and interface-test instructions that accurately describe the current development snapshot.
- AI output: A README covering Python 3.12 virtual-environment setup, demonstration commands, expected outcomes, the public CLI, scope and current verification status.
- Human verification: Lu Wenxi saved the README and displayed its Git diff for inspection. The documented interface-test and missing-checker outcomes refer to previously recorded local runs.
- Verification boundary: The README instructions have not yet been followed from a clean extraction. The real checker and complete demonstration remain unverified.
- Status: Development documentation drafted; independent review and clean-extraction verification are pending.
- Decision: Pending independent review and reproduction checks.
- Evidence: README.md, docs/evidence/bash-python-interface-2026-10-26.txt and docs/evidence/demo-preflight-2026-10-27.txt.
- Remaining risks: Setup instructions, dependencies and expected output must be updated after real-checker and team test-workflow integration, then verified on the unit server.

## Verify — Local clean-extraction reproduction

- Date: 27 October 2026.
- Owner: Lu Wenxi.
- Checker: Yin Jiayu (independent review pending).
- AI tool: OpenAI ChatGPT, https://chatgpt.com/.
- Task and instructions: Check the documented setup and available commands from an extraction containing submitted files without Git history or an existing virtual environment.
- AI output: Commands to export the committed project, extract it, create a new Python 3.12 virtual environment, execute available checks and capture their output.
- Source commit: 917960b09626b7185faf0a701274a731f89f5122.
- Human verification: Lu Wenxi confirmed the extraction initially contained no .git or .venv, created a fresh virtual environment, and executed the recorded commands on macOS using Python 3.12.16, Bash 3.2.57(1)-release and Git 2.50.1.
- Results: The interpreter path pointed to the extracted project's virtual environment. The inventory program reported 3 records and total quantity 10. All six isolated interface test methods passed with exit code 0. The demonstration reported the absent Python checker and returned the expected exit code 2. The verification process returned 0.
- Verification boundary: These results establish the recorded local setup, example execution, interface tests and missing-checker preflight. They do not establish complete checker assessments or successful end-to-end demonstration.
- Status: Recorded local clean-extraction checks passed; independent review and unit-server verification remain pending.
- Decision: Pending independent review.
- Evidence: docs/evidence/clean-extraction-preflight-2026-10-27.txt and README.md.
- Remaining risks: The real checker, demonstration fixture execution, full automated-test and CI workflow, and manual-baseline evaluation require further verification.

## Review follow-up — Demo preflight and development README

- Date: 28 October 2026.
- Owner: Lu Wenxi.
- Independent checker: Yin Jiayu.
- Reviewed version: 43e6751.
- Reviewer-reported environment: macOS 15.7.4, Bash 3.2.57, Git 2.39.5 and a newly created Python 3.12.14 virtual environment.
- Review method: The reviewer exported committed files with git archive and extracted them into a fresh directory without .git or .venv before creating the environment.
- Reviewer-reported results: Both Bash syntax checks and CLI help returned 0. The inventory program reported 3 records and total quantity 10. All six isolated interface test methods passed. Demo preflight reported the missing real checker and returned 2, matching the development README.
- Static inspection: The reviewer inspected submitted inputs, fixture construction, explicit normal/fault commits, retention of the local CSV and expected checker exit-code handling.
- Independent conclusion: No blocking issue was found for the documented preflight stage.
- Owner decision: Accepted for the reviewed development documentation and demo preflight scope. Complete demonstration runtime acceptance remains pending.
- Status update: Independent review is recorded for the exercised scope of the demo, README and clean-extraction activities. Earlier entries retain their historical observations.
- Integration handling: AI-assisted conflict resolution retained both the interface review and demo development records.
- Evidence: Yin Jiayu's review dated 28 October 2026 in MR !5, https://git.infotech.monash.edu/fit2109/fit2109-s2-2026/group-assignment/MY-T06-06/-/merge_requests/5.
- Remaining limitations: The run stopped before fixture construction. Successful complete demonstration, cleanup after fixture creation and final README outcomes require real-checker integration and verification.

## Report drafting — Member A contribution

- Date: 28 October 2026.
- Owner: Lu Wenxi.
- Checker: Yin Jiayu (independent review pending).
- AI tool: OpenAI ChatGPT, https://chatgpt.com/.
- Task and instructions: Draft Member A's scenario explanation, Bash workflow contribution, current verification summary and personal AI-use reflection for the final report.
- AI output: An English contribution draft and AI-use reflection covering the controlled scenario, Bash orchestration, available evidence, expanded AI delegation, shared-assumption risks, the documentation-copying error and remaining verification work.
- Evidence basis: The interface contract, submitted inventory example and recorded local verification results.
- Human action: Lu Wenxi saved the draft in docs/member-a-report-draft.md. Detailed evidence cross-checking and independent review remain pending.
- Verification boundary: This drafting activity produced no new implementation or experimental results.
- Status: Working draft awaiting review and integration into the final group report.
- Decision: Pending review and any resulting revisions.
- Evidence: docs/member-a-report-draft.md and the evidence paths cited within it.
- Remaining risks: Update the draft after real-checker integration and evaluation, verify its claims against evidence, and fit it to the final report requirements and page limit.

## Verify — Unit-server partial reproduction

- Date: 28 October 2026.
- Owner: Lu Wenxi.
- Checker: Yin Jiayu (independent review pending).
- AI tool: OpenAI ChatGPT, https://chatgpt.com/.
- Task and instructions: Prepare and execute scoped checks on the unit server from a clean export, then retain the original results.
- AI output: Commands for archive export, transfer, clean extraction, virtual-environment setup, available checks, log capture and documentation updates.
- Source commit: d63f209516f26837da2b05496cb9137967abe448.
- Human verification: Lu Wenxi executed the commands on fit2109s2.rep.monash.edu using Python 3.12.3, Bash 5.2.21 and Git 2.43.0, inspected the output and downloaded the original log.
- Results: The extraction initially contained no .git or .venv. Environment creation, both Bash syntax checks, CLI help, inventory execution and all six isolated interface test methods passed. Demo preflight reported the absent checker and returned 2. The verification process returned 0.
- Verification boundary: The interface tests use a controlled Python test double. Complete real-checker assessments and demonstration fixture execution were not exercised.
- Status: Recorded unit-server partial checks passed; independent review and complete workflow verification remain pending.
- Decision: Pending independent review.
- Evidence: docs/evidence/unit-server-preflight-2026-10-28.txt, README.md and docs/member-a-report-draft.md.
- Remaining risks: Repeat clean-extraction verification after real-checker and full test-workflow integration; complete the demonstration and baseline evaluation.

## Design / Build / Verify - Member B Python checker

- Date: 28 October 2026.
- Owner: Yin Jiayu. Independent checker: Wen Chin (review pending).
- Tool: OpenAI Codex.
- Task/instructions: Implement the agreed six-argument Python checker; validate checklist paths and raw Git/ZIP evidence; return PASS/0, FAIL/1 or ERROR/2; run real local checks before reporting results.
- Output: Python implementation, regression tests, sample checklist, standard-library test runner, design notes and a draft Member B report contribution.
- Design choices proposed for review: Keep exact ZIP path matching; reject ambiguous JSON/ZIP duplicates; treat unrelated status as context; retain selected-commit requirements; do not claim content/provenance validation. Alternatives and scope are documented in docs/python-checker.md.
- Executed verification: 32 local test methods passed using Python 3.12.14. The real checker produced the expected PASS/0 and FAIL/1 demo outcomes and the demo returned 0. Exact commands/results are in docs/evidence/python-checker-2026-10-28.txt.
- Verification method: Automated local executions and source inspection in this assisted session. These executions are not an independent human peer review. Wen Chin must check expectations and reproduce the branch before merge.
- Decision: Proposed implementation retained for review; final owner/peer acceptance remains pending. No verification or personal design decisions are attributed to a human who has not yet performed them.
- Remaining risks: Implementation and tests were drafted in the same session and may share assumptions. Independent review, full unit-server reproduction, CI and baseline evaluation remain outstanding. Report drafting produces no new experimental evidence.
- Evidence: src/handoff_check.py, tests/test_python_checker.py, docs/python-checker.md, docs/member-b-report-draft.md and the local evidence log.

## Verify / Revise - Member B peer-review corrections

- Date: 28 October 2026.
- Owner: Yin Jiayu. Independent reviewer: Chin Wen Hui (wchi0071).
- Tool: OpenAI Codex.
- Trigger: Chin Wen Hui reviewed commit 77dc8fa63136d092ce4eee1cefc2b76271664119 in MR !7, reproduced B1/B2 and requested changes. Her review is independent evidence, not replaced by the local assisted checks below.
- Assisted work: Reproduced the reported corrupt-DEFLATE and raw-status-name failures with regression tests, revised exception/context handling and diagnostics, and updated the documented policy boundaries.
- Results: Added 13 regression methods; all 45 local methods passed under Python 3.12.14, and both demo cases produced expected 0/1 exits with demo exit 0. The new tests failed against the original implementation before the fixes were applied.
- Verification limits: Permission/I/O, EOF and unexpected internal-error branches are fault-injected. The corrupt compressed ZIP and unusual Git filenames use real files through the public Bash entry point. No new unit-server or CI execution is claimed.
- Decisions still requiring human confirmation: Re-review of B1/B2 and the related S1-S4 changes; explicit acceptance or revision of the defensive duplicate/path policies identified in S5. Current policy tests document behaviour and are not proof of team agreement.
- Evidence: src/handoff_check.py, tests/test_python_checker.py, docs/python-checker.md and MR !7. A clean ZIP extraction of c1f8c455eb28d41b1cf277778d6fa74d0df66153 passed all 45 tests, three Bash syntax checks and both demos in a fresh Python 3.12.14 environment; actual commands, output and limits are retained in docs/evidence/python-review-fixes-2026-10-28.txt.

## Review follow-up — Report draft and server evidence

- Date: 28 October 2026.
- Owner: Lu Wenxi.
- Independent checker: Yin Jiayu.
- Reviewed documentation version: 128330d.
- Server-tested source version: d63f209516f26837da2b05496cb9137967abe448.
- Review method: The reviewer cross-checked the README and Member A draft against the original local logs, interface implementation/tests and original unit-server preflight log.
- Reviewer findings: The server log identifies Python 3.12.3, Bash 5.2.21 and Git 2.43.0, six successful interface test methods, the expected inventory output and missing-checker demo exit code 2. The README and draft distinguish these partial checks from a complete real-checker demonstration. The described Bash responsibilities match the implementation.
- Independent conclusion: No blocking documentation inconsistency was found.
- Review boundary: This was an evidence/documentation review. The reviewer did not independently rerun the remote server commands.
- Owner decision: Accepted for the reviewed documentation and evidence-consistency scope. The report remains a working draft.
- Status update: Independent documentation review is recorded for the report draft and server-evidence descriptions. Independent remote re-execution and complete workflow verification are not established by this review.
- Integration handling: AI-assisted conflict resolution retained the demo review, report-drafting activity and unit-server partial-verification activity.
- Evidence: Yin Jiayu's review dated 28 October 2026 in MR !6, https://git.infotech.monash.edu/fit2109/fit2109-s2-2026/group-assignment/MY-T06-06/-/merge_requests/6.
- Remaining limitations: Update current-status text after real-checker integration, repeat complete clean-extraction verification on the unit server, and incorporate CI and baseline-evaluation results.

## Verify — Member A real-checker integration

- Date: 4 November 2026.
- Owner: Lu Wenxi.
- Originally planned checker: Yin Jiayu.
- Independent reviewer: Chin Wen Hui (wchi0071); see the 5 November 2026 MR !8 follow-up below.
- AI tool: OpenAI ChatGPT, https://chatgpt.com/.
- Task and instructions: Verify the real Bash/Python workflow locally and from a clean ZIP extraction on the unit server, retaining actual test, demonstration and cleanup results.
- AI output: Commands for an isolated local worktree, clean archive export and checksum verification, SSH transfer, fresh Python environments, offline requirements installation, syntax checks, tests, demonstration, cleanup checks and original-log capture.
- Tested source commit: 71d7472d7e920b2bba64327e9b69c3c18ecacd60.
- Human verification: Lu Wenxi executed the local checks using Python 3.12.16, Bash 3.2.57 and Git 2.50.1, then executed the clean-extraction checks on fit2109s2.rep.monash.edu using Python 3.12.3, Bash 5.2.21 and Git 2.43.0. Both original logs were retained.
- Results: All three Bash syntax checks and all 45 test methods passed in both environments. Each complete handoff returned PASS/0; each missing-CSV handoff returned FAIL/1 with findings and a suggested action. Both demonstrations returned 0 and temporary-workspace cleanup checks passed. The local worktree remained clean. The server ZIP checksum matched, and the extraction initially contained neither .git nor .venv.
- Verification boundary: Both runs assessed source commit 71d7472d7e920b2bba64327e9b69c3c18ecacd60. These results do not establish CI execution, measured manual-baseline improvement or correctness of a different final integrated revision.
- Initial status (4 November 2026): Recorded local integration and unit-server clean-extraction tests and demonstration passed; independent evidence review is pending.
- Initial decision (4 November 2026): Pending independent evidence review.
- Evidence: docs/evidence/local-real-checker-2026-11-04.txt and docs/evidence/unit-server-real-checker-2026-11-04.txt.
- Initial remaining risks (4 November 2026): Obtain independent evidence review, confirm the final integrated revision matches the tested implementation, and complete CI and manual-baseline evaluation.

## Verify — CI configuration and runner review

- Date: 4 November 2026.
- Owner: Lu Wenxi.
- Originally planned checker: Yin Jiayu.
- Independent reviewer: Chin Wen Hui (wchi0071); see the 5 November 2026 MR !8 follow-up below.
- AI tool: OpenAI ChatGPT, https://chatgpt.com/.
- Task and instructions: Interpret the CI configuration, pipeline failure and runner screenshots, and draft an evidence-based review record.
- AI output: A scoped diagnosis, runner-inspection guidance and an English review record.
- Human verification: Lu Wenxi inspected the committed YAML using Git and viewed the pipeline failure and runner pages. No CI job was executed as part of this review.
- Findings: The smoke job has no matching runner and no execution log. Project runner #922 was Offline. The configuration prints environment versions but does not execute the full tests or demonstration.
- Initial status (4 November 2026): CI execution remains blocked; follow-up work has been requested from the CI author.
- Initial decision (4 November 2026): No acceptance of successful CI execution. Independent review of this record is pending.
- Evidence: docs/evidence/ci-review-2026-11-04.md and pipeline #166423.
- Initial remaining risks (4 November 2026): Runner compatibility and job matching remain unresolved. Successful smoke execution and complete test/demo CI execution require actual logs and follow-up review.

## Review follow-up — MR !8 evidence and CI smoke

- Date: 5 November 2026.
- Owner: Lu Wenxi.
- Independent reviewer: Chin Wen Hui (wchi0071). Her review assessed commit 6074230 in MR !8; confirmation of this updated documentation remains pending.
- Review method: Chin read all four changed files and compared the two retained logs with her independent WSL2/Linux run of the same checker source, 71d7472d7e920b2bba64327e9b69c3c18ecacd60. She did not rerun the macOS or unit-server commands.
- Accepted evidence: The recorded 45 test methods, normal PASS/0, missing-CSV FAIL/1, demo exit 0 and cleanup results were accepted for the documented source and environments. This is an evidence-consistency review, not independent remote re-execution.
- Changes requested: Update the outdated CI status, synchronise master, and identify the actual independent reviewer. The original local/server logs remain unchanged; individual syntax-check exit codes have not been retrospectively added.
- Later CI evidence: On 4 November, pipeline #166423 job #519084 passed for smoke commit 58a6a491b21661dce097b72ec5b0687c1dccdce8 on project runner #922 using the Docker executor and python:3.12.16-slim. The log printed Python 3.12.16, Git 2.47.3 and Bash 5.2.37.
- Human review: Lu inspected the committed YAML and existing successful job log, requested MR !9 description corrections, and approved the smoke scope after correction. MR !9 was merged. Lu did not independently rerun that job.
- Current CI status: Follow-up items 1, 2, 3 and 6 are resolved for the observed smoke execution. Items 4 and 5 remain open: full test/demo CI and verified failure propagation. Smoke success does not establish execution of project tests or the demonstration.
- Integration handling: Master ea76aaf was merged into this branch without conflicts. Both Member B AI-use entries and Member A's existing records were retained.
- AI assistance: OpenAI ChatGPT helped interpret the review, draft these corrections and prepare Git/document-update commands. This documentation update produces no new runtime or timing evidence.
- Owner decision: Retain the accepted verification evidence and smoke-scope result; modify the status and reviewer records as requested. The revised MR remains subject to follow-up review.
- Remaining risks: Runner host/process availability, full CI, measured manual-baseline evaluation and final submitted-revision verification remain separate work.
- Evidence: MR !8 review; MR !9 review and merge; docs/evidence/ci-review-2026-11-04.md; the unchanged local and unit-server logs.
- Review link: https://git.infotech.monash.edu/fit2109/fit2109-s2-2026/group-assignment/MY-T06-06/-/merge_requests/8
- Smoke job: https://git.infotech.monash.edu/fit2109/fit2109-s2-2026/group-assignment/MY-T06-06/-/jobs/519084

## Verify / Evaluate — Final archive audit and aggregation checks

- Date: 6 November 2026.
- Owner: Lu Wenxi.
- Independent checkers: Yin Jiayu (jyin0039) and Chin Wen Hui (wchi0071), MR !21, 6 November 2026.
- Review evidence: Yin approved the initial MR revision. Chin reviewed all five files against repository evidence, confirming the test breakdown, duration history, execution attribution and commit references.
- Review outcome: Chin requested clarification of workflow-need validation, reviewer attribution and the pipeline reference. Chin re-reviewed af372f43 in MR !21, confirmed the corrections and approved the revised documentation.
- AI tool: OpenAI ChatGPT, including automated checks in its separate analysis environment.
- Task and instructions: Check the exported project against the assignment specification and rubric, reproduce the submitted evaluation summary, inspect the sensitivity analyses, and identify remaining submission gaps.
- AI output: An evidence-based review, automated test and demonstration results, aggregation checks, and suggested documentation corrections.
- Reviewed archive: MY-T06-06-preflight-075625d.zip, exported from commit 075625db8834f14b83f46266b3475937fcd07fe3.
- Automated verification: In a fresh Linux extraction without Git history or an existing virtual environment, the assistant created a Python 3.12.14 environment. Requirements processing, four Bash syntax checks, all 90 tests and the demonstration passed. The demonstration produced the expected checker exits 0 and 1 and returned 0 overall.
- Evaluation checks: Regenerating summary.md produced a byte-for-byte match. The additional excluding-Chin analysis confirmed six unflagged Lu pairs: correctness 6/6 for both methods, median commands 5/2, judgements 16/2.5 and time 34/25 seconds.
- Human-led responsibilities: Lu supplied the committed archive and course documents, retained responsibility for interpreting the findings and selecting revisions, and will obtain independent review before integration.
- Owner decision: Modified. Use the findings for documentation corrections and submission planning while keeping their environment and scope explicit. Do not present assistant-executed checks as Lu's macOS execution or as course unit-server verification.
- Verification boundary: This activity occurred after measurement and did not change the raw logs or measured values. It does not establish stopwatch endpoints, contemporaneous cognitive judgements, final PDF compliance or video quality.
- Findings requiring follow-up: Update outdated README and checker-review status, complete the team's later AI-use records, and verify the final submission revision from a clean extraction on the unit server.
- Evidence: The reviewed archive; docs/evaluation-runs/summary.md; docs/evaluation.md Sections 8–10; the ChatGPT review conversation and its recorded execution results.
- Remaining risks: Automated tests can share assumptions with the implementation. Follow-up review of the revised record in MR !21 and final unit-server verification remain pending.

## Verify / Evaluate — Later peer reviews and report integration

- Activity dates: 5–6 November 2026. Recorded retrospectively on 6 November 2026.
- Owner: Lu Wenxi.
- Independent checkers: Yin Jiayu (jyin0039) and Chin Wen Hui (wchi0071), MR !21, 6 November 2026.
- Review evidence: Yin approved the initial MR revision. Chin reviewed all five files against repository evidence, confirming the test breakdown, duration history, execution attribution and commit references.
- Review outcome: Chin requested clarification of workflow-need validation, reviewer attribution and the pipeline reference. Chin re-reviewed af372f43 in MR !21, confirmed the corrections and approved the revised documentation.
- AI tool: OpenAI ChatGPT.
- Task and instructions: Help inspect later test, evaluation and reproducibility changes; compare claims with submitted evidence; draft review comments and update the final report without overstating verification or measurement quality.
- AI output: Review suggestions, controlled failure-propagation commands, automated calculations in a separate analysis environment, English MR comments and revised report paragraphs.
- Human verification: For MR !12, Lu ran the suite and demonstration locally on macOS with Python 3.12.16, recording 65 passing tests and one filesystem-dependent skip. Local stand-in checks exercised the CI wrappers and the effect of pipefail. These were not deliberately failing GitLab jobs.
- Later review evidence: MRs !16–!20 document evaluation-record qualifications, aggregation validation defects, fixes, frozen-checker reproducibility and revised interpretation. Relevant reviewed revisions include b576dfd for MR !17, bcfa359 for MR !18 and cd6763ce for MR !20.
- Execution attribution: Later Linux/Python 3.12.14 automated checks were performed in the assistant's separate environment. They are distinct from Lu's macOS execution, supplied CI artifacts and retained unit-server logs.
- Owner decision: Modified. Retain findings supported by code, records or execution; distinguish recorded and analysis verdicts; preserve timing qualifications; report both flagged-pair exclusions and the additional excluding-Chin sensitivity view.
- Report assistance: ChatGPT drafted and revised English explanations, AI reflections, contribution statements and review comments. This writing assistance produced no new measurement evidence. Each member remains responsible for confirming their own statements.
- Measurement boundary: For Lu's sixteen retained timed runs, ChatGPT was used for preparation before timing. Lu independently executed the assessments, interpreted outputs and recorded conclusions before stopping the timer. Later assistance with review and report wording does not change that account.
- Evidence: MRs !12, !14 and !16–!20; docs/evaluation.md; docs/evaluation-runs/summary.md; member CSV files and logs; the final report and ChatGPT conversation.
- Remaining risks: Retrospective judgement counts are not contemporaneous cognitive tallies; terminal logs do not independently prove stopwatch endpoints. Chin completed follow-up review of the revised record in MR !21. Course-server verification of commit 3f79104 is recorded below; later submission changes still require reconciliation.

## Verify — Integrated snapshot on the course unit server

- Date: 6 November 2026.
- Owner and executor: Lu Wenxi.
- Independent checker: Chin Wen Hui (wchi0071), MR !22, 6 November 2026. Chin reviewed the original logs, test count, demo outcomes, exact summary match, extraction conditions and execution attribution. He requested that this record identify the completed review.
- AI tool: OpenAI ChatGPT.
- Task and instructions: Prepare a versioned archive, transfer and checksum checks, clean extraction, Python 3.12 setup, test/demo execution and original-log retention.
- AI output: Terminal commands, evidence-checking assistance and draft documentation.
- Human verification: Lu executed the commands on fit2109s2.rep.monash.edu using a new Python 3.12.3 environment, Git 2.43.0 and Bash 5.2.21.
- Tested source: 3f79104196643a4f58480c3e7422a656fd7849d8.
- Results: The source checksum matched; initial extraction had no .git or .venv; 90 tests passed without skips; demo returned 0 with expected checker exits 0 and 1; the saved-record summary matched exactly; no checker temporary directories remained; verification_exit=0.
- Owner decision: Accepted as execution evidence for the documented commit and environment following Chin's evidence review in MR !22. The original source ZIP is attached to that MR; independent verification of its attachment checksum has not yet been recorded.
- Attribution: Commands were AI-assisted; course-server execution was performed by Lu. Recomputing stored cross-environment results was not a new CI execution.
- Evidence: docs/evidence/unit-server-2026-11-06-3f79104/.
- Remaining risks: This run does not validate every later revision or establish measured user-effort savings. The controlled-scenario and evaluation limitations remain applicable.

## Design — Member B proposal and AI delegation plan

- Activity date / retrospectively recorded date: October 2026 / 6 November 2026.
- Stage and task: Draft Member B's proposed tool, technical approach and AI delegation activity for Handoff Check.
- Owner: Yin Jiayu.
- Independent checker: Pending.
- Actual AI tool: OpenAI Codex desktop.
- Instructions: Explain the proposal requirements, clarify Member B's responsibilities and suggest wording for the checker design and AI declaration.
- Output: A proposal draft and design options for team discussion.
  - Yin identified which sections she needed to cover and asked for wording that reflected her responsibilities. The team retained decisions on scope, severity and exit behaviour.
  - The assistant suggested wording, checklist formats, finding categories and a possible order for the checks.
- Decision: Accepted for planning only. Yin used the suggestions to organise ideas and wrote the submitted text herself.
- Remaining risks: The proposal describes a plan. Record any later change in the actual division of work separately.

## Verify — Inventory scenario peer reviews (MR !1 and !2)

- Activity date / retrospectively recorded date: October 2026 / 6 November 2026.
- Stage and task: Review the inventory scenario and report the findings in GitLab.
- Owner: Yin Jiayu.
- Independent checker: Pending for this AI-use record.
- Actual AI tool: OpenAI Codex desktop.
- Instructions: Run the example locally, explain the normal and missing-CSV outcomes and draft concise review comments. Describe MR !1 as a post-merge review.
- Output: Review notes for the complete handoff and the missing CSV case.
  - Yin chose how to report the reviews and specified that the MR !1 review took place after the merge.
  - The assistant ran local reproduction checks and suggested wording for the review comments.
- Decision: Modified. The MR !1 note was scoped to a post-merge check. Follow-up review on MR !2 addressed the revised documentation.
- Remaining risks: The local reproduction was scoped to the inventory fixture. The MR !1 check happened after the merge.

## Verify — Bash workflow peer reviews (MR !3–!6)

- Activity date / retrospectively recorded date: 24–28 October 2026 / 6 November 2026.
- Stage and task: Review ZIP handling, the Bash-to-Python interface, demo setup and development documentation.
- Owner: Yin Jiayu.
- Independent checker: Pending for this AI-use record.
- Actual AI tool: OpenAI Codex desktop.
- Instructions: Inspect the changed files, run scoped local checks in isolated copies and draft comments with the checked commit, commands and observed results.
- Output: Review comments on the ZIP handling, interface and preflight checks. The server documentation review compared existing logs with the written claims.
  - Yin was responsible for the peer review and the conclusions reported on each MR.
  - The assistant helped inspect the changes, ran local checks and drafted comments.
- Decision: Modified. The review comments retained the tested scope of each MR.
- Remaining risks: The interface tests used a Python test double. The server documentation review used existing logs, and the earlier preflight was scoped to the development snapshot.

## Build — Checklist diagnostic follow-up (MR !13)

- Activity date / retrospectively recorded date: 5 November 2026 / 6 November 2026.
- Stage and task: Build. Implement the checklist diagnostic fix for Issue #2 and prepare it for team review.
- Owner: Yin Jiayu.
- Independent checker: Chin Wen Hui approved the implementation in MR !13. Review of this AI-use entry is pending in MR !24.
- Actual AI tool: OpenAI Codex desktop.
- Instructions: Fix the checklist diagnostic so it names the requested path and ref. Keep the change separate from the frozen evaluation and prepare it for peer review.
- Output: MR !13 displays the requested checklist path and ref in the public error and returns `ERROR` with exit code `2`.
  - Yin used Codex to help fix the checklist diagnostic and requested a teammate's review. Codex generated and applied the patch and ran the local checks, including the test suite and demo.
- Decision: Accepted for the merged diagnostic change. The evaluation continued with frozen commit `71d7472`.
- Remaining risks: The local suite had one filesystem-dependent skip. The timed evaluation used the earlier frozen build.

## Verify — Evaluation setup and separate scripted runs

- Activity date / retrospectively recorded date: 5 November 2026 / 6 November 2026.
- Stage and task: Prepare Yin's evaluation environment and exercise the eight cases under both methods.
- Owner: Yin Jiayu.
- Independent checker: Chin Wen Hui (MR !15 review). Review of this AI-use entry is pending.
- Actual AI tool: OpenAI Codex desktop.
- Instructions: Prepare the frozen checker, fixtures, run order and results sheet. Run the procedures on the local Mac and capture terminal output.
- Output: A run guide, a results sheet and a separate set of scripted logs.
  - Yin requested a setup for her assigned case order and later completed her own timed sessions.
  - The assistant prepared the materials and executed the scripted checks for both methods across all eight cases.
- Decision: Modified. The team kept the scripted logs as supplementary material and repeated the timed evaluation with separate terminal transcripts.
- Remaining risks: Scripted wall times describe automated execution. Human timing and judgement metrics come from the participant sessions and their recorded limitations.

## Verify — Timed evaluation reruns and results recording (MR !15)

- Activity date / retrospectively recorded date: 6 November 2026 / 6 November 2026.
- Stage and task: Repeat the 16 runs, record terminal sessions, and prepare Yin's results CSV and README.
- Owner: Yin Jiayu.
- Independent checker: Chin Wen Hui (MR !15 review). Review of this AI-use entry is pending.
- Actual AI tool: OpenAI Codex desktop.
- Instructions: Give the next command for each case, help interpret terminal output, and enter verdicts and diagnostics in the CSV. Use the elapsed times reported by Yin, who operated the stopwatch.
- Output: Terminal transcripts and a results CSV for the 16 runs with frozen checker commit `71d7472`.
  - Yin ran the terminal commands, operated the stopwatch, supplied the elapsed times and confirmed how repeated commands were handled.
  - The assistant suggested commands and helped interpret the output and enter verdicts and diagnostics in the CSV.
- Decision: Modified. Keep the rows in the all-results analysis and flag them as `ai-assisted`. Keep the three unconfirmed manual timings flagged as `time-inconsistent`.
- Remaining risks: AI guidance may affect diagnosis and timing. Three reported manual times exceed the gaps between the corresponding terminal sessions.

## Verify — Local demo check for Member B

- Activity date / retrospectively recorded date: 6 November 2026 / 6 November 2026.
- Stage and task: Verify. Run the existing demo locally and check the output for both handoff cases.
- Owner: Yin Jiayu.
- Independent checker: Pending.
- Actual AI tool: OpenAI Codex desktop.
- Instructions: Run the demo and identify the terminal output that shows each case's result.
- Output: Codex ran the demo locally. The complete handoff returned `PASS` with exit code `0`, and the missing CSV case returned `FAIL` with exit code `1`.
- Decision: Used the output as a reference for the terminal lines to show in the video.
- Remaining risks: This check covered the two demo cases on the local machine.

## Video preparation — Member B narration

- Activity date / retrospectively recorded date: 6 November 2026 / 6 November 2026.
- Stage and task: Prepare narration for Yin's 90-second demonstration. Script assistance does not count as a technical AI activity.
- Owner: Yin Jiayu.
- Independent checker: Pending.
- Actual AI tool: OpenAI Codex desktop.
- Instructions: Suggest a spoken English script and an order for presenting the two cases.
- Output: Draft narration and presentation cues. Yin set the 90-second format and recorded her own explanation of the checker.
- Decision: Modified. Yin used the draft and demonstration order as a guide and recorded the explanation in her own words.
- Remaining risks: Check that the terminal output is readable and the segment fits the time budget in the final team edit.
