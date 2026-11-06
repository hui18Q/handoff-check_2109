#!/usr/bin/env bash
# Reproducibility run for evaluation.md §8.6.
#
# Regenerates the eight evaluation fixtures, runs the FROZEN checker
# (commit 71d7472, evaluation.md §5.1) on each case, and writes per-case
# exit code, stdout and stderr to OUTDIR so that two environments (GitLab CI
# and the unit server) can be compared with:
#     python3 scripts/aggregate_eval.py --repro OUTDIR_A OUTDIR_B
#
# Usage (project root, Python 3.12 virtual environment active):
#     bash scripts/repro_eval.sh OUTDIR
#
# OUTDIR must not exist. Needs the full Git history (the frozen commit must
# be reachable); in GitLab CI set GIT_DEPTH to 0.
# Exit: 0 when all eight cases ran (whatever their verdicts), 2 on setup error.

set -u
set -o pipefail

FROZEN=71d7472d7e920b2bba64327e9b69c3c18ecacd60

die() { printf 'ERROR: %s\n' "$1" >&2; exit 2; }

[ $# -eq 1 ] || die "usage: bash scripts/repro_eval.sh OUTDIR"
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P) || die "cannot locate project root"
cd -- "$root" || die "cannot enter project root"

python3 -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)' \
    || die "activate a Python 3.12 virtual environment"
git cat-file -e "${FROZEN}^{commit}" 2>/dev/null \
    || die "frozen checker commit $FROZEN is not available; fetch full history (git fetch --unshallow, or GIT_DEPTH=0 in CI)"

out=$1
[ -e "$out" ] && die "OUTDIR already exists: $out"
mkdir -p -- "$out" || die "cannot create $out"
out=$(cd -- "$out" && pwd -P)

work=$(mktemp -d) || die "mktemp failed"
fixtures="$root/.scenario-runs/repro-fixtures.$$"
cleanup() { rm -rf -- "$work" "$fixtures"; }
trap cleanup EXIT

# Frozen checker: an exact export of the frozen commit, outside the project.
checker="$work/checker"
mkdir -p -- "$checker"
git archive --format=tar "$FROZEN" | tar -x -C "$checker" || die "cannot export frozen checker"

normalise() {
    # evaluation.md §8.6: fixture root -> <FIXTURES>, temp checklist dir -> <TMP>;
    # the exported checker directory is also machine-specific -> <CHECKER>.
    sed -e "s|$fixtures|<FIXTURES>|g" -e "s|$checker|<CHECKER>|g" \
        -E -e 's|\.handoff-tmp\.[A-Za-z0-9]+|<TMP>|g'
}

# Fixtures from the current generator; commit IDs and ZIP hashes are recorded
# in summary.csv for comparison with evaluation.md §2.3.
python3 scripts/make_fixtures.py --output "$fixtures" > "$work/fixtures.txt" 2>&1 \
    || { cat -- "$work/fixtures.txt" >&2; die "fixture generation failed"; }
normalise < "$work/fixtures.txt" > "$out/fixtures.txt"

{
    printf 'date: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'host: %s\n' "$(uname -srm)"
    printf 'project_commit: %s\n' "$(git rev-parse HEAD)"
    printf 'checker_commit: %s\n' "$FROZEN"
    printf 'python: %s\n' "$(python3 --version 2>&1)"
    printf 'git: %s\n' "$(git --version)"
    printf 'bash: %s\n' "$BASH_VERSION"
} > "$out/environment.txt"

# One line per case: id <TAB> commit <TAB> zip_sha256 <TAB> checker command.
python3 - "$fixtures/manifest.json" > "$work/cases.tsv" <<'PY' || die "cannot read manifest"
import json, sys
for c in json.load(open(sys.argv[1], encoding="utf-8"))["cases"]:
    print("\t".join([c["id"], c["commit"], c["zip_sha256"] or "-", c["checker_command"]]))
PY

printf 'case,commit,zip_sha256,exit,verdict\n' > "$out/summary.csv"
while IFS=$'\t' read -r id commit zipsha command; do
    (cd -- "$checker" && eval "$command") > "$work/$id.stdout" 2> "$work/$id.stderr"
    code=$?
    normalise < "$work/$id.stdout" > "$out/$id.stdout"
    normalise < "$work/$id.stderr" > "$out/$id.stderr"
    printf '%s\n' "$code" > "$out/$id.exit"
    case $code in 0) verdict=PASS ;; 1) verdict=FAIL ;; 2) verdict=ERROR ;; *) verdict=UNEXPECTED ;; esac
    printf '%s,%s,%s,%s,%s\n' "$id" "$commit" "$zipsha" "$code" "$verdict" >> "$out/summary.csv"
    printf '%s  exit %s  %s\n' "$id" "$code" "$verdict"
done < "$work/cases.tsv"

printf 'Results written to %s\n' "$out"
exit 0
