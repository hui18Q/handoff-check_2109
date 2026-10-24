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
  --repo PATH       Local, non-bare Git working repository (required).
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

repo_path=""
target_ref="HEAD"
checklist_path="handoff-check.json"
zip_path=""

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

# Replaced by repository validation in the next development step.
printf 'ERROR: Repository checking is not implemented in this development step.\n' >&2
exit 2
