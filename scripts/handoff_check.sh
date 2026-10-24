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

repo_path=""
target_ref="HEAD"
checklist_path="handoff-check.json"
zip_path=""
tool_root=""
temp_workspace=""

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
collect_evidence

printf 'Repository: %s\n' "$repo_root"
printf 'Selected commit: %s\n' "$commit_id"
printf 'Temporary workspace: %s\n' "$temp_workspace"
printf 'Checklist and Git evidence collected.\n'

# Replaced by archive handling and Python integration in later steps.
printf 'ERROR: Archive and Python checks are not implemented in this development step.\n' >&2
exit 2