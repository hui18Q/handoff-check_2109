"""Build the eight Handoff Check evaluation fixtures (proposal Section 4).

Each case is a separate Git repository under OUTPUT/case-NN/repo. Cases that
need a supplied ZIP also get OUTPUT/case-NN/handoff.zip. Every case directory
has an INPUTS.txt naming the target ref, checklist, ZIP and exact checker
command; OUTPUT/manifest.json records the same data for scripts.

Builds are deterministic: file contents are fixed LF bytes, Git runs with
system/global configuration disabled and a fixed author, committer and date,
and supplied ZIPs are written with fixed timestamps and no compression. The
same commit IDs and ZIP SHA-256 values are therefore produced on every machine.

Expected outcomes are deliberately not written into the case directories; they
are recorded in docs/evaluation.md before either method is run.

Usage (from the project root):
    python3 scripts/make_fixtures.py [--output DIR]

Exit codes: 0 fixtures built; 2 invalid output location or a command failed.
"""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / ".scenario-runs" / "eval-fixtures"

FIXTURE_NAME = "Handoff Fixture"
FIXTURE_EMAIL = "fixture@example.invalid"
FIXTURE_DATE = "2026-10-20T10:00:00+11:00"
ZIP_DATE_TIME = (2026, 10, 20, 10, 0, 0)
TARGET_REF = "main"
CHECKLIST = "handoff-check.json"

README = """# Inventory Report

Reads data/items.csv and prints the record count and total quantity.

Run from the project directory:

    python3 report.py

Expected output:

    Records: 3
    Total quantity: 10
"""

REPORT_PY = """import csv
from pathlib import Path

input_file = Path(__file__).resolve().parent / "data" / "items.csv"

with input_file.open(newline="", encoding="utf-8") as file:
    rows = list(csv.DictReader(file))

print(f"Records: {len(rows)}")
print(f"Total quantity: {sum(int(row['quantity']) for row in rows)}")
"""

ITEMS_CSV = """item,quantity
Notebook,2
Pen,5
Folder,3
"""

VALID_CHECKLIST = """{
  "required_files": [
    "README.md",
    "report.py",
    "data/items.csv"
  ]
}
"""

# Case 05: the third entry escapes the repository (parent traversal).
TRAVERSAL_CHECKLIST = """{
  "required_files": [
    "README.md",
    "report.py",
    "../data/items.csv"
  ]
}
"""

PROJECT_FILES = {
    "README.md": README,
    "report.py": REPORT_PY,
    "data/items.csv": ITEMS_CSV,
    CHECKLIST: VALID_CHECKLIST,
}


def git_env():
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": FIXTURE_NAME,
        "GIT_AUTHOR_EMAIL": FIXTURE_EMAIL,
        "GIT_AUTHOR_DATE": FIXTURE_DATE,
        "GIT_COMMITTER_NAME": FIXTURE_NAME,
        "GIT_COMMITTER_EMAIL": FIXTURE_EMAIL,
        "GIT_COMMITTER_DATE": FIXTURE_DATE,
    })
    return env


def git(repo, *args):
    command = ["git", "-C", str(repo),
               "-c", "core.autocrlf=false",
               "-c", "core.hooksPath=" + os.devnull,
               "-c", "core.attributesFile=" + os.devnull,
               "-c", "commit.gpgSign=false",
               *args]
    result = subprocess.run(command, env=git_env(), check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout.strip()


def write_files(repo, files):
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))


def commit_repo(repo, files, tracked, message):
    """Create a one-commit repository on TARGET_REF; untracked files stay local."""
    repo.mkdir(parents=True)
    git(repo, "init", "--quiet", "--template=", "--initial-branch=" + TARGET_REF)
    write_files(repo, files)
    git(repo, "add", "--", *tracked)
    git(repo, "commit", "--quiet", "-m", message)
    return git(repo, "rev-parse", "--verify", TARGET_REF + "^{commit}")


def zip_bytes(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in files.items():
            info = zipfile.ZipInfo(name, date_time=ZIP_DATE_TIME)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, text.encode("utf-8"))
    return buffer.getvalue()


def build_case(case_dir, number):
    """Build one case and return (zip bytes or None, target ref)."""
    repo = case_dir / "repo"
    message = f"Prepare inventory report handoff (fixture {number:02d})"
    all_paths = list(PROJECT_FILES)
    supplied_zip = None
    ref = TARGET_REF

    if number == 1:
        # Complete handoff.
        commit_repo(repo, PROJECT_FILES, all_paths, message)
    elif number == 2:
        # Required CSV exists locally but was never added to the commit.
        commit_repo(repo, PROJECT_FILES, ["README.md", "report.py", CHECKLIST], message)
    elif number == 3:
        # Required CSV is committed but excluded from git archive by export-ignore.
        files = {**PROJECT_FILES, ".gitattributes": "data/items.csv export-ignore\n"}
        commit_repo(repo, files, list(files), message)
    elif number == 4:
        # Complete handoff plus an unrelated untracked note and an ignored log.
        files = {**PROJECT_FILES, ".gitignore": "*.log\n"}
        commit_repo(repo, files, list(files), message)
        write_files(repo, {"notes/todo.txt": "Ask receiver about Python version.\n",
                           "report.log": "Records: 3\nTotal quantity: 10\n"})
    elif number == 5:
        # Committed checklist contains a parent-traversal path.
        files = {**PROJECT_FILES, CHECKLIST: TRAVERSAL_CHECKLIST}
        commit_repo(repo, files, list(files), message)
    elif number == 6:
        # Complete repository, but the requested release tag was never created.
        commit_repo(repo, PROJECT_FILES, all_paths, message)
        ref = "v1.0"
    elif number == 7:
        # Complete commit; the supplied ZIP was packed by hand without the CSV.
        commit_repo(repo, PROJECT_FILES, all_paths, message)
        supplied_zip = zip_bytes({name: PROJECT_FILES[name]
                                  for name in ("README.md", "report.py", CHECKLIST)})
    elif number == 8:
        # Complete commit; the supplied ZIP is truncated (interrupted copy).
        commit_repo(repo, PROJECT_FILES, all_paths, message)
        complete = zip_bytes(PROJECT_FILES)
        supplied_zip = complete[:len(complete) // 2]
    else:
        raise ValueError(f"Unknown case number: {number}")

    return supplied_zip, ref


def checker_command(repo, ref, zip_path):
    command = f"bash scripts/handoff_check.sh --repo {repo} --ref {ref} --checklist {CHECKLIST}"
    if zip_path is not None:
        command += f" --zip {zip_path}"
    return command


def inputs_text(case_id, repo, ref, zip_path, manual_zip, command):
    zip_line = (str(zip_path) if zip_path is not None
                else "none supplied - generate one from the target ref")
    lines = [
        f"Case: {case_id}",
        f"Repository: {repo}",
        f"Target ref: {ref}",
        f"Checklist: {CHECKLIST} (read from the target ref)",
        f"ZIP: {zip_line}",
    ]
    if zip_path is None:
        lines.append(f"Manual baseline archive output: {manual_zip}")
    lines += ["", "Checker command (run from the tool project root):", f"  {command}", ""]
    return "\n".join(lines)


def build_fixtures(output):
    """Build all cases under output and return the manifest dictionary."""
    output.mkdir(parents=True)
    manifest = {"target_ref_default": TARGET_REF, "checklist": CHECKLIST, "cases": []}

    for number in range(1, 9):
        case_id = f"case-{number:02d}"
        case_dir = output / case_id
        repo = case_dir / "repo"
        supplied_zip, ref = build_case(case_dir, number)

        zip_path = None
        zip_sha256 = None
        if supplied_zip is not None:
            zip_path = case_dir / "handoff.zip"
            zip_path.write_bytes(supplied_zip)
            zip_sha256 = hashlib.sha256(supplied_zip).hexdigest()

        manual_zip = case_dir / "manual-handoff.zip"
        command = checker_command(repo, ref, zip_path)
        (case_dir / "INPUTS.txt").write_bytes(
            inputs_text(case_id, repo, ref, zip_path, manual_zip, command).encode("utf-8"))

        manifest["cases"].append({
            "id": case_id,
            "repo": str(repo),
            "ref": ref,
            "commit": git(repo, "rev-parse", "--verify", TARGET_REF + "^{commit}"),
            "checklist": CHECKLIST,
            "zip": str(zip_path) if zip_path is not None else None,
            "zip_sha256": zip_sha256,
            "manual_zip": str(manual_zip) if zip_path is None else None,
            "checker_command": command,
        })

    (output / "manifest.json").write_bytes(
        (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="new directory inside the project "
                             "(default: .scenario-runs/eval-fixtures)")
    args = parser.parse_args(argv)

    output = args.output.resolve()
    if output == PROJECT_ROOT or PROJECT_ROOT not in output.parents:
        print(f"ERROR: --output must be inside the project directory: {output}", file=sys.stderr)
        return 2
    if output.exists():
        print(f"ERROR: output already exists; remove it or choose another: {output}",
              file=sys.stderr)
        return 2

    try:
        manifest = build_fixtures(output)
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: command failed ({exc.returncode}): {' '.join(exc.cmd)}\n{exc.stderr}",
              file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    for case in manifest["cases"]:
        zip_note = f"  zip sha256 {case['zip_sha256']}" if case["zip_sha256"] else ""
        print(f"{case['id']}  ref {case['ref']:<5} commit {case['commit']}{zip_note}")
    print(f"Fixtures written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
