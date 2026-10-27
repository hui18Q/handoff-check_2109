#!/usr/bin/env bash
set -u
set -o pipefail

error() {
    printf 'ERROR: %s\n' "$1" >&2
    exit 2
}

cleanup() {
    local result=$?
    trap - EXIT

    if [ -n "$workspace" ]; then
        if ! rm -rf -- "$workspace"; then
            printf 'ERROR: Cannot remove demo workspace: %s\n' \
                "$workspace" >&2
            exit 2
        fi
    fi

    exit "$result"
}

fixture_git() {
    GIT_CONFIG_NOSYSTEM=1 \
    GIT_CONFIG_GLOBAL=/dev/null \
    GIT_ATTR_NOSYSTEM=1 \
    git -C "$fixture_repo" \
        -c core.hooksPath=/dev/null \
        -c core.attributesFile=/dev/null \
        -c commit.gpgSign=false \
        -c user.name="Handoff Demo" \
        -c user.email="demo@example.invalid" \
        "$@"
}

run_case() {
    local label="$1"
    local selected_commit="$2"
    local expected_exit="$3"
    local actual_exit

    printf '\n=== %s ===\n' "$label"
    printf 'Expected checker exit code: %s\n' "$expected_exit"

    if bash "$tool_root/scripts/handoff_check.sh" \
        --repo "$fixture_repo" \
        --ref "$selected_commit"; then
        actual_exit=0
    else
        actual_exit=$?
    fi

    printf 'Actual checker exit code: %s\n' "$actual_exit"

    if [ "$actual_exit" -ne "$expected_exit" ]; then
        error "Unexpected checker exit code for: $label"
    fi
}

workspace=""
tool_root=""
fixture_repo=""

if [ "$#" -ne 0 ]; then
    error "This demo takes no arguments. Run: bash scripts/demo.sh"
fi

for required_command in git python3 dirname mktemp mkdir cp rm; do
    if ! command -v "$required_command" >/dev/null 2>&1; then
        error "Required command is unavailable: $required_command"
    fi
done

if ! tool_root=$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P
); then
    error "Cannot determine the tool project root."
fi

if ! python3 -c \
    'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)'; then
    error "Python 3.12 is required. Activate the project virtual environment."
fi

if [ ! -r "$tool_root/scripts/handoff_check.sh" ]; then
    error "Bash checker is missing or unreadable."
fi

if [ ! -f "$tool_root/src/handoff_check.py" ] ||
   [ ! -r "$tool_root/src/handoff_check.py" ]; then
    error "Python checker is missing or unreadable: $tool_root/src/handoff_check.py"
fi

scenario_source="$tool_root/scenarios/inventory-report"

for source_file in README.md report.py data/items.csv; do
    if [ ! -f "$scenario_source/$source_file" ] ||
       [ ! -r "$scenario_source/$source_file" ]; then
        error "Demo source is missing or unreadable: $source_file"
    fi
done

trap cleanup EXIT
trap 'error "Demo interrupted by SIGHUP."' HUP
trap 'error "Demo interrupted by SIGINT."' INT
trap 'error "Demo interrupted by SIGTERM."' TERM

if ! mkdir -p "$tool_root/.scenario-runs"; then
    error "Cannot create the demo workspace parent directory."
fi

if ! workspace=$(
    mktemp -d "$tool_root/.scenario-runs/demo.XXXXXXXX"
); then
    error "Cannot create the demo workspace."
fi

fixture_repo="$workspace/inventory"

if ! mkdir -p "$fixture_repo/data"; then
    error "Cannot create the demo repository directory."
fi

if ! cp "$scenario_source/README.md" "$fixture_repo/README.md" ||
   ! cp "$scenario_source/report.py" "$fixture_repo/report.py" ||
   ! cp "$scenario_source/data/items.csv" "$fixture_repo/data/items.csv"; then
    error "Cannot copy the submitted inventory scenario."
fi

if ! printf '%s\n' \
    '{"required_files":["README.md","report.py","data/items.csv"]}' \
    > "$fixture_repo/handoff-check.json"; then
    error "Cannot write the demo checklist."
fi

if ! fixture_git init --quiet; then
    error "Cannot initialise the demo Git repository."
fi

if ! fixture_git add -- \
    README.md report.py data/items.csv handoff-check.json; then
    error "Cannot stage the complete demo scenario."
fi

if ! fixture_git commit --quiet -m "Create complete inventory handoff"; then
    error "Cannot commit the complete demo scenario."
fi

if ! normal_commit=$(fixture_git rev-parse --verify HEAD); then
    error "Cannot resolve the normal demo commit."
fi

if ! fixture_git rm --quiet --cached -- data/items.csv; then
    error "Cannot prepare the missing-file scenario."
fi

if ! printf '%s\n' '/data/items.csv' > "$fixture_repo/.gitignore"; then
    error "Cannot write the demo ignore rule."
fi

if ! fixture_git add -- .gitignore; then
    error "Cannot stage the demo ignore rule."
fi

if ! fixture_git commit --quiet -m "Omit required CSV from handoff"; then
    error "Cannot commit the missing-file scenario."
fi

if ! missing_commit=$(fixture_git rev-parse --verify HEAD); then
    error "Cannot resolve the missing-file demo commit."
fi

if [ ! -f "$fixture_repo/data/items.csv" ]; then
    error "The missing-file scenario must retain the local CSV."
fi

run_case "Complete selected commit" "$normal_commit" 0
run_case "Required CSV exists locally but is absent from commit" \
    "$missing_commit" 1

printf '\nDemo completed: both checker exit codes matched expectations.\n'
exit 0