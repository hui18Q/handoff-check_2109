#!/usr/bin/env bash
set -u
set -o pipefail

show_help() {
    cat <<'EOF'
Usage:
  bash scripts/handoff_check.sh --repo PATH [--ref REF]
      [--checklist PATH] [--zip PATH]
  bash scripts/handoff_check.sh --help

Options:
  --repo PATH       Root directory of a local Git working repository (required).
  --ref REF         Commit or ref to check (default: HEAD).
  --checklist PATH  Repository-relative checklist path in the selected commit
                    (default: handoff-check.json).
  --zip PATH        Existing ZIP to check; otherwise generate a temporary ZIP.
  --help, -h        Show this help and exit without running a check.

Requirements:
  Git and Python 3.12 available on PATH.

Completed-check exit codes:
  0  PASS: required regular files exist in the selected commit and ZIP.
  1  FAIL: a required regular file is missing or has an unsupported type.
  2  ERROR: invalid input or a required operation failed.

Scope:
  Checks required-file presence, not content equality or program correctness.
EOF
}

argument_error() {
    printf 'ERROR: %s\n' "$1" >&2
    printf 'Run bash scripts/handoff_check.sh --help for usage.\n' >&2
    exit 2
}

require_value() {
    if [ "$#" -lt 2 ]; then
        argument_error "Option $1 requires a value."
    fi

    if [ -z "$2" ]; then
        argument_error "Option $1 requires a non-empty value."
    fi

    case "$2" in
        --*|-h)
            argument_error "Option $1 requires a value before $2."
            ;;
    esac
}

operational_error() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 2
}

validate_checklist_path() {
    case "$checklist_path" in
        /*|*/|*//*)
            argument_error "--checklist must be a canonical repository-relative file path."
            ;;
    esac

    case "/$checklist_path/" in
        */./*|*/../*)
            argument_error "--checklist must not contain . or .. path components."
            ;;
    esac
}

validate_repository() {
    local inside_work_tree
    local repo_prefix

    if ! command -v git >/dev/null 2>&1; then
        operational_error "Git is not installed or not available on PATH."
    fi

    if [ ! -d "$repo_path" ]; then
        operational_error "Repository path is not a directory: $repo_path"
    fi

    if ! inside_work_tree=$(git -C "$repo_path" rev-parse --is-inside-work-tree 2>/dev/null); then
        operational_error "Cannot access a Git repository at: $repo_path"
    fi

    if [ "$inside_work_tree" != "true" ]; then
        operational_error "Repository must have a working tree; bare repositories are not supported."
    fi

    if ! repo_prefix=$(git -C "$repo_path" rev-parse --show-prefix 2>/dev/null); then
        operational_error "Cannot determine the repository-relative location: $repo_path"
    fi

    if [ -n "$repo_prefix" ]; then
        operational_error "--repo must name the repository root, not a subdirectory: $repo_path"
    fi

    if ! repo_root=$(git -C "$repo_path" rev-parse --show-toplevel 2>/dev/null); then
        operational_error "Cannot determine the repository root: $repo_path"
    fi

    repo_path="$repo_root"
}

resolve_target_commit() {
    if ! commit_id=$(git -C "$repo_root" rev-parse --verify --end-of-options "${target_ref}^{commit}" 2>/dev/null); then
        operational_error "Ref does not resolve to an available commit: $target_ref"
    fi
}

cleanup() {
    local exit_code=$?
    trap - EXIT

    if [ -n "$temp_workspace" ]; then
        if ! rm -rf -- "$temp_workspace"; then
            printf 'ERROR: Cannot remove temporary workspace: %s\n' "$temp_workspace" >&2
            exit 2
        fi
    fi

    exit "$exit_code"
}

initialize_workspace() {
    local required_command

    for required_command in dirname mktemp rm; do
        if ! command -v "$required_command" >/dev/null 2>&1; then
            operational_error "Required command is not available: $required_command"
        fi
    done

    if ! tool_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P); then
        operational_error "Cannot determine the tool project root."
    fi

    trap cleanup EXIT
    trap 'operational_error "Interrupted by SIGHUP."' HUP
    trap 'operational_error "Interrupted by SIGINT."' INT
    trap 'operational_error "Interrupted by SIGTERM."' TERM

    if ! temp_workspace=$(mktemp -d "$tool_root/.handoff-tmp.XXXXXXXX"); then
        operational_error "Cannot create a temporary workspace inside the tool project."
    fi

    checklist_file="$temp_workspace/checklist.json"
    status_file="$temp_workspace/status.bin"
    tree_file="$temp_workspace/tree.bin"
}

validate_python() {
    if ! command -v python3 >/dev/null 2>&1; then
        operational_error "Python 3.12 is not available on PATH."
    fi

    if ! python3 -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)'; then
        operational_error "Python 3.12 is required. Activate the project's Python 3.12 virtual environment."
    fi

    checker_script="$tool_root/src/handoff_check.py"

    if [ ! -f "$checker_script" ] || [ ! -r "$checker_script" ]; then
        operational_error "Python checker is missing or unreadable: $checker_script"
    fi
}

collect_evidence() {
    if ! git -C "$repo_root" cat-file blob "${commit_id}:${checklist_path}" > "$checklist_file"; then
        operational_error "Cannot read checklist from the selected commit: $checklist_path"
    fi

    if ! GIT_OPTIONAL_LOCKS=0 git -c core.fsmonitor=false -C "$repo_root" \
        status --porcelain=v1 -z --untracked-files=all --ignored > "$status_file"; then
        operational_error "Cannot collect working-tree status."
    fi

    if ! git -C "$repo_root" ls-tree -r -z --full-tree "$commit_id" > "$tree_file"; then
        operational_error "Cannot inspect the selected commit tree."
    fi
}

prepare_archive() {
    if [ -n "$zip_path" ]; then
        case "$zip_path" in
            /*)
                archive_path="$zip_path"
                ;;
            *)
                archive_path="$PWD/$zip_path"
                ;;
        esac

        if [ ! -f "$archive_path" ] || [ ! -r "$archive_path" ]; then
            operational_error "Supplied ZIP is not a readable file: $archive_path"
        fi
    else
        archive_path="$temp_workspace/handoff.zip"

        if ! git -C "$repo_root" archive \
            --format=zip --output="$archive_path" "$commit_id"; then
            operational_error "Cannot generate a ZIP from the selected commit."
        fi
    fi
}

run_checker() {
    local checker_exit

    python3 "$checker_script" \
        --repo "$repo_root" \
        --commit "$commit_id" \
        --checklist "$checklist_file" \
        --status-file "$status_file" \
        --tree-file "$tree_file" \
        --archive "$archive_path"
    checker_exit=$?

    case "$checker_exit" in
        0|1|2)
            exit "$checker_exit"
            ;;
        *)
            operational_error "Python checker returned an unsupported exit code: $checker_exit"
            ;;
    esac
}

repo_path=""
target_ref="HEAD"
checklist_path="handoff-check.json"
zip_path=""
archive_path=""
tool_root=""
temp_workspace=""
checker_script=""

while [ "$#" -gt 0 ]; do
    case "$1" in
        --repo)
            require_value "$@"
            repo_path="$2"
            shift 2
            ;;
        --ref)
            require_value "$@"
            target_ref="$2"
            shift 2
            ;;
        --checklist)
            require_value "$@"
            checklist_path="$2"
            shift 2
            ;;
        --zip)
            require_value "$@"
            zip_path="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            argument_error "Unknown argument: $1"
            ;;
    esac
done

if [ -z "$repo_path" ]; then
    argument_error "Missing required option: --repo"
fi

validate_checklist_path
validate_repository
resolve_target_commit
initialize_workspace
validate_python
collect_evidence
prepare_archive
run_checker
