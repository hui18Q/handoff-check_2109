#!/usr/bin/env bash
set -u
set -o pipefail

if ! tool_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P); then
    printf 'ERROR: Cannot locate the project root.\n' >&2
    exit 2
fi
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)'; then
    printf 'ERROR: Activate a Python 3.12 virtual environment.\n' >&2
    exit 2
fi
cd -- "$tool_root" || exit 2
python3 -m unittest discover -s tests -p 'test_*.py' -v
