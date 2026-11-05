"""Real-checker tests with explicit expected verdicts, not a Python test double."""

import importlib.util
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("handoff_check", PROJECT / "src/handoff_check.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class RealCheckerTests(unittest.TestCase):
    def setUp(self):
        parent = PROJECT / ".scenario-runs"
        parent.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="python-checker-", dir=parent)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo with spaces"
        self.repo.mkdir()
        self.env = os.environ.copy()
        self.env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + self.env.get("PATH", "")
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
            self.env.pop(key, None)
        self.env.update(GIT_OPTIONAL_LOCKS="0", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        self.git("init", "-q")
        (self.repo / "README.md").write_text("Fixture\n", encoding="utf-8")
        (self.repo / "data").mkdir()
        (self.repo / "data/items.csv").write_text("quantity\n10\n", encoding="utf-8")
        self.set_checklist(["README.md", "data/items.csv"])
        self.commit("Complete fixture")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], env=self.env,
                              check=True, capture_output=True).stdout

    def commit(self, message):
        self.git("add", ".")
        self.git("-c", "core.hooksPath=/dev/null", "-c", "commit.gpgSign=false",
                 "-c", "user.name=Checker test fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "-qm", message)
        return self.git("rev-parse", "HEAD").decode().strip()

    def set_checklist(self, required):
        (self.repo / "handoff-check.json").write_text(json.dumps({"required_files": required}) + "\n", encoding="utf-8")

    def run_bash(self, *extra, expected=0):
        before = self.snapshot()
        result = subprocess.run(["bash", str(PROJECT / "scripts/handoff_check.sh"),
                                 "--repo", str(self.repo), *extra], cwd=self.root,
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stderr + result.stdout)
        self.assertEqual(self.snapshot(), before, "Checker changed the target repository.")
        self.assertFalse(list(PROJECT.glob(".handoff-tmp.*")))
        if expected in (0, 1):
            self.assertEqual(result.stderr, "")
            self.assertIn("Result: " + ("PASS" if expected == 0 else "FAIL"), result.stdout)
        else:
            self.assertEqual(result.stdout, "")
            self.assertIn("ERROR:", result.stderr)
        return result

    def snapshot(self):
        return {str(p.relative_to(self.repo)): (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns)
                for p in self.repo.rglob("*") if p.is_file() and not p.is_symlink()}

    def make_zip(self, entries, name="supplied handoff.zip"):
        path = self.root / name
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(path, "w") as archive:
                for entry, contents in entries:
                    archive.writestr(entry, contents)
        return path

    def complete_entries(self):
        return [("README.md", "Fixture\n"), ("data/items.csv", "quantity\n10\n")]

    def test_complete_generated_archive(self):
        result = self.run_bash()
        self.assertIn("selected commit: regular; ZIP: regular", result.stdout)

    def test_missing_commit_file_retained_locally(self):
        self.git("rm", "--cached", "data/items.csv")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Omit CSV")
        self.assertTrue((self.repo / "data/items.csv").is_file())
        result = self.run_bash(expected=1)
        self.assertIn("working tree: regular", result.stdout)
        self.assertIn("selected commit: missing; ZIP: missing", result.stdout)
        self.assertIn("Suggested action:", result.stdout)

    def test_export_ignore_omission(self):
        (self.repo / ".gitattributes").write_text("data/items.csv export-ignore\n")
        self.commit("Exclude CSV from archive")
        result = self.run_bash(expected=1)
        self.assertIn("selected commit: regular; ZIP: missing", result.stdout)

    def test_unrelated_untracked_and_ignored_do_not_fail(self):
        (self.repo / ".gitignore").write_text("ignored.txt\n")
        self.commit("Ignore unrelated file")
        (self.repo / "ignored.txt").write_text("irrelevant")
        (self.repo / "untracked.txt").write_text("irrelevant")
        self.run_bash()

    def test_working_absence_does_not_fail(self):
        (self.repo / "data/items.csv").unlink()
        result = self.run_bash()
        self.assertIn("working tree: missing", result.stdout)

    def test_selected_commit_and_committed_checklist(self):
        selected = self.git("rev-parse", "HEAD").decode().strip()
        self.set_checklist(["NOT_PRESENT.txt"])
        self.commit("Later checklist")
        self.set_checklist(["LOCAL_ONLY.txt"])
        result = self.run_bash("--ref", selected)
        self.assertIn(selected, result.stdout)
        self.assertNotIn("LOCAL_ONLY", result.stdout)
        self.assertNotIn("NOT_PRESENT", result.stdout)

    def test_supplied_archive_paths_and_preservation(self):
        archive = self.make_zip(self.complete_entries())
        before = (archive.read_bytes(), archive.stat().st_mtime_ns)
        for path in (str(archive), archive.name):
            with self.subTest(path=path):
                self.run_bash("--zip", path)
                self.assertEqual((archive.read_bytes(), archive.stat().st_mtime_ns), before)

    def test_supplied_archive_omission(self):
        archive = self.make_zip([("README.md", "Fixture")])
        self.run_bash("--zip", str(archive), expected=1)

    def test_top_level_zip_prefix_is_not_removed(self):
        archive = self.make_zip([("project/" + name, data) for name, data in self.complete_entries()])
        self.run_bash("--zip", str(archive), expected=1)

    def test_case_sensitive_archive_match(self):
        archive = self.make_zip([("readme.md", "wrong case"), ("data/items.csv", "10")])
        self.run_bash("--zip", str(archive), expected=1)

    def test_spaces_and_newlines_in_required_names(self):
        for name in ("name with spaces.txt", "line\nname.txt"):
            (self.repo / name).write_text("present")
        self.set_checklist(["name with spaces.txt", "line\nname.txt"])
        self.commit("Unusual filenames")
        self.git("mv", "name with spaces.txt", "renamed file.txt")
        result = self.run_bash()
        self.assertIn('"line\\nname.txt"', result.stdout)
        self.assertIn("renamed to", result.stdout)

    def test_symlink_in_commit_is_not_regular(self):
        (self.repo / "link.txt").symlink_to("README.md")
        self.set_checklist(["link.txt"])
        self.commit("Symlink requirement")
        result = self.run_bash(expected=1)
        self.assertIn("selected commit: symlink; ZIP: symlink", result.stdout)

    def test_directory_requirement_is_not_regular(self):
        self.set_checklist(["data"])
        self.commit("Directory requirement")
        result = self.run_bash(expected=1)
        self.assertIn("selected commit: directory; ZIP: directory", result.stdout)

    def test_zip_symlink_does_not_satisfy_regular_file(self):
        entry = zipfile.ZipInfo("data/items.csv")
        entry.create_system = 3
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive = self.make_zip([("README.md", "present"), (entry, "README.md")])
        result = self.run_bash("--zip", str(archive), expected=1)
        self.assertIn("ZIP: symlink", result.stdout)

    def test_zip_special_file_is_not_regular(self):
        entry = zipfile.ZipInfo("data/items.csv")
        entry.create_system = 3
        entry.external_attr = (stat.S_IFIFO | 0o600) << 16
        archive = self.make_zip([("README.md", "present"), (entry, "")])
        self.run_bash("--zip", str(archive), expected=1)

    def test_invalid_archive_paths(self):
        for bad in ("../escape.txt", "/absolute.txt", "a//b.txt"):
            with self.subTest(path=bad):
                archive = self.make_zip(self.complete_entries() + [(bad, "invalid")])
                self.run_bash("--zip", str(archive), expected=2)

    def test_duplicate_zip_entry_is_error(self):
        archive = self.make_zip(self.complete_entries() + [("README.md", "duplicate")])
        self.run_bash("--zip", str(archive), expected=2)

    def test_corrupt_zip_is_error(self):
        archive = self.root / "corrupt.zip"
        archive.write_bytes(b"not a zip")
        self.run_bash("--zip", str(archive), expected=2)

    def test_zip_crc_error_prevents_verdict(self):
        archive = self.make_zip(self.complete_entries())
        data = bytearray(archive.read_bytes())
        offset = data.index(b"Fixture\n")
        data[offset] ^= 1
        archive.write_bytes(data)
        self.run_bash("--zip", str(archive), expected=2)

    def test_malformed_json_is_error(self):
        (self.repo / "handoff-check.json").write_text("{not JSON}")
        self.commit("Invalid JSON")
        self.run_bash(expected=2)

    def test_checklist_error_names_user_path_and_ref_not_temporary_copy(self):
        (self.repo / "review list.json").write_text('{"required_files":["../data/items.csv"]}\n')
        self.commit("Invalid alternate checklist")
        self.git("tag", "review/bad")
        with mock.patch.dict(self.env, {"HANDOFF_CHECKLIST_SOURCE": "ignored parent value"}):
            first = self.run_bash("--checklist", "review list.json", "--ref", "review/bad", expected=2)
            second = self.run_bash("--checklist", "review list.json", "--ref", "review/bad", expected=2)
        self.assertIn("review list.json @ review/bad", first.stderr)
        self.assertIn("required_files[0]", first.stderr)
        self.assertNotIn(".handoff-tmp.", first.stderr)
        self.assertEqual(first.stderr, second.stderr)

    def test_duplicate_json_key_is_error(self):
        (self.repo / "handoff-check.json").write_text('{"required_files":["absent"],"required_files":["README.md"]}')
        self.commit("Ambiguous JSON")
        self.run_bash(expected=2)

    def test_checklist_schema_and_path_rejections(self):
        for invalid in ([], {}, {"required_files": []}, {"required_files": "README.md"},
                        {"required_files": [123]}, {"required_files": [""]},
                        {"required_files": ["README.md", "README.md"]},
                        {"required_files": ["../escape"]}, {"required_files": ["/absolute"]},
                        {"required_files": ["a//b"]}, {"required_files": ["./README.md"]},
                        {"required_files": ["a\0b"]}):
            with self.subTest(checklist=invalid):
                path = self.root / "bad.json"
                path.write_text(json.dumps(invalid))
                with self.assertRaises(checker.InputError):
                    checker.read_checklist(path)

    def test_invalid_git_evidence_rejected(self):
        for data in (b"not nul terminated", b"\0", b"bogus\0", b"100644 blob invalid\tREADME.md\0"):
            with self.subTest(tree=data):
                path = self.root / "bad-tree.bin"
                path.write_bytes(data)
                with self.assertRaises(checker.InputError):
                    checker.read_tree(path)
        for data in (b"?? no-terminator", b"bad\0", b"XX file\0", b"R  new\0"):
            with self.subTest(status=data):
                path = self.root / "bad-status.bin"
                path.write_bytes(data)
                with self.assertRaises(checker.InputError):
                    checker.read_status(path)

    def test_working_symlink_ancestor_not_followed(self):
        (self.repo / "outside-link").symlink_to(self.root, target_is_directory=True)
        self.assertEqual(checker.working_kind(self.repo, "outside-link/file.txt"), "symlink ancestor")

    def test_invalid_ref_missing_archive_and_checklist(self):
        self.run_bash("--ref", "NOT_A_REF", expected=2)
        self.run_bash("--zip", "missing.zip", expected=2)
        self.run_bash("--checklist", "missing.json", expected=2)

    def test_no_arguments_is_error(self):
        result = subprocess.run([sys.executable, str(PROJECT / "src/handoff_check.py")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")

    def test_corrupt_deflated_zip_is_error_not_fail(self):
        archive = self.root / "broken compressed.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
            for name, contents in self.complete_entries():
                package.writestr(name, contents)
        with zipfile.ZipFile(archive) as package:
            entry = package.getinfo("README.md")
            offset = entry.header_offset
        data = bytearray(archive.read_bytes())
        name_size, extra_size = struct.unpack_from("<HH", data, offset + 26)
        # BTYPE=3 is invalid DEFLATE, unlike a stored-entry CRC mismatch.
        data[offset + 30 + name_size + extra_size] = 0xFF
        archive.write_bytes(data)
        result = self.run_bash("--zip", str(archive), expected=2)
        self.assertIn(str(archive), result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_unrelated_unusual_status_names_are_context_only(self):
        names = ["notes\\draft.txt", "C:notes.txt", "ignored\\cache.txt", "D:cache.txt"]
        (self.repo / ".gitignore").write_text("ignored*\nD:*\n")
        self.commit("Ignore unusual context names")
        for name in names:
            (self.repo / name).write_text("not required")
        result = self.run_bash()
        for name in names:
            self.assertIn(checker.quoted(name), result.stdout)

    def test_status_rename_preserves_raw_names(self):
        evidence = self.root / "status.bin"
        evidence.write_bytes(b"R  C:new\\name.txt\0old\\name.txt\0")
        statuses = checker.read_status(evidence)
        self.assertIn("C:new\\name.txt", statuses)
        self.assertIn("old\\name.txt", statuses)

    def test_unrelated_unusual_tree_and_zip_names_do_not_fail(self):
        for name in ("back\\slash.txt", "C:notes.txt"):
            (self.repo / name).write_text("not required")
        self.commit("Unusual but unrelated tracked names")
        self.run_bash()
        archive = self.make_zip(self.complete_entries() + [
            ("C:/file.txt", "not a checklist path"), ("back\\slash.txt", "not required")])
        self.run_bash("--zip", str(archive))

    def test_local_permission_failure_is_informational(self):
        with mock.patch.object(checker.Path, "lstat", side_effect=PermissionError("denied")):
            self.assertEqual(checker.working_kind(self.repo, "README.md"), "inaccessible")

    def test_local_io_failure_does_not_change_verdict(self):
        args = self.internal_arguments()
        with mock.patch.object(checker.Path, "lstat", side_effect=OSError("local I/O error")):
            report, code = checker.assess(args)
        self.assertEqual(code, 0)
        self.assertIn("working tree: inaccessible", report)

    def internal_arguments(self):
        from argparse import Namespace
        status = self.root / "status.bin"
        tree = self.root / "tree.bin"
        status.write_bytes(self.git("status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored"))
        tree.write_bytes(self.git("ls-tree", "-r", "-z", "--full-tree", "HEAD"))
        return Namespace(repo=self.repo, commit=self.git("rev-parse", "HEAD").decode().strip(),
                         checklist=self.repo / "handoff-check.json", status_file=status,
                         tree_file=tree, archive=self.make_zip(self.complete_entries()))

    def test_checklist_error_names_source_and_position(self):
        cases = [('{"required_files":["README.md",123]}', "required_files[1]"),
                 ('{"required_files":["README.md","README.md"]}', "required_files[1]"),
                 ('{\nnot JSON}', "line 2"),
                 ('{"required_files":["/etc/passwd"]}', "Absolute paths")]
        for contents, detail in cases:
            with self.subTest(contents=contents):
                args = self.internal_arguments()
                args.checklist = self.root / "invalid checklist.json"
                args.checklist.write_text(contents)
                with self.assertRaises(checker.InputError) as raised:
                    checker.assess(args)
                self.assertIn(str(args.checklist), str(raised.exception))
                self.assertIn(detail, str(raised.exception))

    def test_bad_zip_error_names_input(self):
        archive = self.root / "bad archive.zip"
        archive.write_bytes(b"not ZIP")
        result = self.run_bash("--zip", str(archive), expected=2)
        self.assertIn(str(archive), result.stderr)

    def test_bad_repository_error_names_input(self):
        args = self.internal_arguments()
        args.repo = self.root / "absent repository"
        with self.assertRaises(checker.InputError) as raised:
            checker.assess(args)
        self.assertIn(str(args.repo), str(raised.exception))

    def test_archive_eof_error_names_input(self):
        archive = self.make_zip(self.complete_entries())
        with mock.patch.object(checker.zipfile.ZipFile, "testzip", side_effect=EOFError("truncated stream")):
            with self.assertRaises(checker.InputError) as raised:
                checker.read_archive(archive)
        self.assertIn(str(archive), str(raised.exception))

    def test_fail_reason_names_each_actual_location(self):
        args = self.internal_arguments()
        args.archive = self.make_zip([("README.md", "present")])
        report, code = checker.assess(args)
        self.assertEqual(code, 1)
        reason = next(line for line in report.splitlines() if "Reason:" in line)
        self.assertIn("ZIP: missing", reason)
        self.assertNotIn("selected commit:", reason)
        args.tree_file.write_bytes(b"")
        report, code = checker.assess(args)
        self.assertEqual(code, 1)
        self.assertIn("selected commit: missing; ZIP: missing", report.split("Reason:")[-1])

    def test_commit_only_failure_reason_does_not_blame_zip(self):
        args = self.internal_arguments()
        args.tree_file.write_bytes(b"")
        report, code = checker.assess(args)
        self.assertEqual(code, 1)
        reasons = [line for line in report.splitlines() if "Reason:" in line]
        self.assertEqual(len(reasons), 2)
        for reason in reasons:
            self.assertIn("selected commit: missing", reason)
            self.assertNotIn("ZIP:", reason)

    def test_unexpected_internal_exception_returns_error_without_traceback(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        args = self.internal_arguments()
        argv = []
        for option, value in vars(args).items():
            argv.extend(["--" + option.replace("_", "-"), str(value)])
        with mock.patch.object(checker, "assess", side_effect=TypeError("internal bug")):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = checker.main(argv)
        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("ERROR:", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
