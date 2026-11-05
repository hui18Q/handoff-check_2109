"""Assess required regular-file presence using the Bash evidence contract.

The checker reads evidence and ZIP entries; it never extracts an archive or
changes the inspected repository. Presence is not a content/provenance check.
"""

import argparse
from functools import wraps
import json
import os
from pathlib import Path
import re
import stat
import sys
import zipfile
import zlib


class InputError(ValueError):
    """An assessment cannot be made from the supplied input."""


def quoted(value):
    """Keep filenames with newlines/control characters on a single report line."""
    return json.dumps(value, ensure_ascii=True)


def input_source(label):
    """Keep operational/format failures tied to the input being read."""
    def decorate(reader):
        @wraps(reader)
        def read(path, *, display_path=None):
            try:
                return reader(path)
            except (OSError, ValueError, RuntimeError, NotImplementedError,
                    zipfile.BadZipFile, zipfile.LargeZipFile, zlib.error, EOFError) as exc:
                source = path if display_path is None else display_path
                # The label already identifies the input; OSError may otherwise
                # include the physical filename of its temporary copy.
                detail = (exc.strerror or str(exc)) if isinstance(exc, OSError) else str(exc)
                raise InputError(f"{label} {quoted(str(source))}: {detail}") from exc
        return read
    return decorate


def validate_path(value, *, portable=True):
    if not isinstance(value, str) or not value or "\0" in value:
        raise InputError("Each required path must be a non-empty string without NUL.")
    if value.startswith("/"):
        raise InputError(f"Absolute paths are not allowed: {quoted(value)}")
    if portable and ("\\" in value or re.match(r"^[A-Za-z]:", value)):
        raise InputError(f"Use repository-relative paths with / separators: {quoted(value)}")
    if any(part in ("", ".", "..") for part in value.split("/")):
        raise InputError(f"Non-canonical repository-relative path: {quoted(value)}")
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"Duplicate JSON key: {quoted(key)}")
        result[key] = value
    return result


@input_source("Checklist")
def read_checklist(path):
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    if not isinstance(data, dict):
        raise InputError("Checklist must be a JSON object.")
    required = data.get("required_files")
    if not isinstance(required, list) or not required:
        raise InputError("required_files must be a non-empty array.")
    paths = []
    first_index = {}
    for index, item in enumerate(required):
        try:
            name = validate_path(item)
        except InputError as exc:
            raise InputError(f"required_files[{index}]: {exc}") from exc
        if name in first_index:
            raise InputError(f"required_files[{index}] duplicates required_files[{first_index[name]}]: {quoted(name)}")
        first_index[name] = index
        paths.append(name)
    return paths


def nul_records(data, label):
    if not data:
        return []
    if not data.endswith(b"\0"):
        raise InputError(f"{label} evidence is not NUL-terminated.")
    records = data[:-1].split(b"\0")
    if any(not record for record in records):
        raise InputError(f"{label} evidence contains an empty record.")
    return records


@input_source("Tree evidence")
def read_tree(path):
    entries = {}
    modes = {b"100644": (b"blob", "regular"), b"100755": (b"blob", "regular"),
             b"120000": (b"blob", "symlink"), b"160000": (b"commit", "submodule"),
             b"040000": (b"tree", "directory")}
    for record in nul_records(path.read_bytes(), "Tree"):
        try:
            header, raw_name = record.split(b"\t", 1)
            mode, kind, oid = header.split(b" ")
        except ValueError as exc:
            raise InputError("Malformed ls-tree evidence record.") from exc
        if mode not in modes or modes[mode][0] != kind or not re.fullmatch(b"[0-9a-f]{40}|[0-9a-f]{64}", oid):
            raise InputError("Invalid mode/type/object ID in tree evidence.")
        name = validate_path(os.fsdecode(raw_name), portable=False)
        if name in entries:
            raise InputError(f"Duplicate tree path: {quoted(name)}")
        entries[name] = modes[mode][1]
    return entries


@input_source("Status evidence")
def read_status(path):
    records = iter(nul_records(path.read_bytes(), "Status"))
    statuses = {}
    for record in records:
        if len(record) < 4 or record[2:3] != b" ":
            raise InputError("Malformed porcelain-v1 status record.")
        code = record[:2]
        if code not in (b"??", b"!!") and (
            code == b"  " or any(char not in b" MADRCUT" for char in code)
        ):
            raise InputError("Invalid porcelain-v1 status code.")
        name = os.fsdecode(record[3:])
        # Status is context, not a checklist: preserve Git's exact raw names.
        # NUL framing and the status/header structure are validated above.
        statuses[name] = code.decode("ascii")
        if b"R" in code or b"C" in code:
            try:
                original = os.fsdecode(next(records))
            except StopIteration as exc:
                raise InputError("Rename/copy status lacks its source path.") from exc
            # With -z Git reports the destination first and source second.
            if b"R" in code:
                statuses.setdefault(original, "renamed to " + quoted(name))
    return statuses


@input_source("ZIP archive")
def read_archive(path):
    entries = {}
    with zipfile.ZipFile(path) as archive:
        for item in archive.infolist():
            name = item.orig_filename
            is_directory = item.is_dir()
            canonical = validate_path(name[:-1] if is_directory else name, portable=False)
            if canonical in entries:
                raise InputError(f"Duplicate or conflicting ZIP path: {quoted(canonical)}")
            mode = item.external_attr >> 16 if item.create_system == 3 else 0
            file_type = stat.S_IFMT(mode)
            if is_directory or file_type == stat.S_IFDIR:
                kind = "directory"
            elif file_type == stat.S_IFLNK:
                kind = "symlink"
            elif file_type in (0, stat.S_IFREG):
                kind = "regular"
            else:
                kind = "unsupported type"
            entries[canonical] = kind
        bad = archive.testzip()
        if bad is not None:
            raise InputError(f"ZIP CRC validation failed for {quoted(bad)}")
    return entries


def stored_kind(entries, name):
    parts = name.split("/")
    for index in range(1, len(parts)):
        ancestor = "/".join(parts[:index])
        if ancestor in entries and entries[ancestor] != "directory":
            return "unsupported ancestor (" + entries[ancestor] + ")"
    if name in entries:
        return entries[name]
    if any(entry.startswith(name + "/") for entry in entries):
        return "directory"
    return "missing"


def working_kind(repo, name):
    current = repo
    parts = name.split("/")
    for index, part in enumerate(parts):
        current = current / part
        try:
            mode = current.lstat().st_mode
        except (FileNotFoundError, NotADirectoryError):
            return "missing"
        except OSError:
            return "inaccessible"
        if stat.S_ISLNK(mode):
            return "symlink" if index == len(parts) - 1 else "symlink ancestor"
        if index < len(parts) - 1 and not stat.S_ISDIR(mode):
            return "non-directory ancestor"
    if stat.S_ISREG(mode):
        return "regular"
    if stat.S_ISDIR(mode):
        return "directory"
    return "unsupported type"


def status_for(statuses, name):
    if name in statuses:
        return statuses[name]
    for path, code in statuses.items():
        if path.endswith("/") and name.startswith(path):
            return code
    return "not listed"


def assess(args):
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", args.commit):
        raise InputError(f"--commit {quoted(args.commit)} must be the full resolved Git commit ID.")
    for name in ("repo", "checklist", "status_file", "tree_file", "archive"):
        if not getattr(args, name).is_absolute():
            raise InputError("Internal path --" + name.replace("_", "-") +
                             f" must be absolute: {quoted(str(getattr(args, name)))}")
    if not args.repo.is_dir():
        raise InputError(f"Repository {quoted(str(args.repo))}: root is not an accessible directory.")

    # Finish validation before printing any assessment or PASS/FAIL result.
    required = read_checklist(
        args.checklist, display_path=os.environ.get("HANDOFF_CHECKLIST_SOURCE") or None
    )
    tree = read_tree(args.tree_file)
    statuses = read_status(args.status_file)
    archive = read_archive(args.archive)
    findings = []
    for name in required:
        local = working_kind(args.repo, name)
        committed = stored_kind(tree, name)
        packaged = stored_kind(archive, name)
        failed = committed != "regular" or packaged != "regular"
        lines = [f"{'FAIL' if failed else 'PASS'} {quoted(name)}",
                 f"  working tree: {local}; Git status: {quoted(status_for(statuses, name))}",
                 f"  selected commit: {committed}; ZIP: {packaged}"]
        if failed:
            locations = []
            if committed != "regular":
                locations.append("selected commit: " + committed)
            if packaged != "regular":
                locations.append("ZIP: " + packaged)
            lines.append("  Reason: required regular file unavailable at " + "; ".join(locations) + ".")
            if committed != "regular":
                lines.append("  Suggested action: track a regular file at this path, commit it, select that commit and rebuild the handoff ZIP.")
            else:
                lines.append("  Suggested action: inspect archive paths and export-ignore/packaging rules, then rebuild a ZIP containing this exact regular-file path.")
        findings.append((failed, lines))

    failures = sum(failed for failed, _ in findings)
    report = [f"Selected commit: {args.commit}", f"Required files: {len(required)}"]
    for _, lines in findings:
        report.extend(lines)
    unrelated = [(path, code) for path, code in statuses.items() if path not in required]
    report.append(f"Other Git status paths: {len(unrelated)} (informational; do not determine the verdict)")
    for path, code in unrelated:
        report.append(f"  Context: {quoted(path)}; Git status: {quoted(code)}")
    report.append(f"Result: {'FAIL' if failures else 'PASS'} ({failures} required-file findings)")
    report.append("Scope: required-file presence only; contents, provenance and program behaviour are not checked.")
    return "\n".join(report) + "\n", 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--commit", required=True)
    for name in ("repo", "checklist", "status-file", "tree-file", "archive"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report, code = assess(args)
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        # Unexpected checker faults must not masquerade as a completed FAIL/1.
        # Do not catch SystemExit/KeyboardInterrupt, and never emit a verdict.
        inputs = ", ".join(f"{name}={quoted(str(getattr(args, name)))}" for name in
                           ("repo", "checklist", "status_file", "tree_file", "archive"))
        print(f"ERROR: unexpected checker failure ({type(exc).__name__}) with {inputs}: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(report)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
