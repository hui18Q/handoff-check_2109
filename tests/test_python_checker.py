"""Real-checker tests with explicit expected verdicts, not a Python test double."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
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
        for bad in ("../escape.txt", "/absolute.txt", "a//b.txt", "C:/file.txt", "back\\slash.txt"):
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


if __name__ == "__main__":
    unittest.main()
