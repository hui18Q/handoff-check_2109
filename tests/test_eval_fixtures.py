"""Evaluation fixtures and extra edge cases run through this repository's checker.

Expected values are copied from docs/evaluation.md (Section 2.3 identifiers and
Section 3 outcomes), never from checker output. The checker is this
repository's scripts/handoff_check.sh, run with the exact command the fixture
generator writes into each case's INPUTS.txt.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
import zipfile


PROJECT = Path(__file__).resolve().parents[1]
CHECKER = PROJECT / "scripts" / "handoff_check.sh"
SPEC = importlib.util.spec_from_file_location("make_fixtures", PROJECT / "scripts" / "make_fixtures.py")
fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixtures)

REQUIRED = ["README.md", "report.py", "data/items.csv"]

# docs/evaluation.md Section 2.3.
REFERENCE_COMMITS = {
    "case-01": "92f067b25ee433ac8b5931dd33b254e65e72581b",
    "case-02": "68edbabdc81c7325b2088dbb95a0fd352ff36876",
    "case-03": "b48d716ebb570b4c4e419d940652de922ce1a8fb",
    "case-04": "d7d3a9dd32a41a550eec314cee9faf4ea8821d43",
    "case-05": "df81a70abb2df6fb63ccd65bf1b91a7e7e1953d4",
    "case-06": "b7e74af8afc475937da3e91c519828ece6b71414",
    "case-07": "65476cfa6ddead9da2d38752e3b744bc752e2293",
    "case-08": "d3c40e761dc83c9c4b5939a094eb58454fce7ded",
}
REFERENCE_ZIP_SHA256 = {
    "case-07": "4d5745dfba9f0075bae111c89987782952a952b547f903c9d32d8f8e7de5d81e",
    "case-08": "64bfb1a5af12db736b33f719f7bdd6a27af37735d906579f65084058480ff17f",
}


def checker_env():
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return env


def git_status(repo):
    return subprocess.run(["git", "-C", str(repo), "status", "--porcelain=v1", "-z",
                           "--untracked-files=all", "--ignored"],
                          env=checker_env(), check=True, capture_output=True).stdout


def findings(report):
    """Map each required path to its report block: [verdict, detail lines...]."""
    blocks, current = {}, None
    for line in report.splitlines():
        if line.startswith(("PASS ", "FAIL ")):
            verdict, name = line.split(" ", 1)
            current = blocks[json.loads(name)] = [verdict]
        elif line.startswith("  ") and current is not None:
            current.append(line.strip())
        else:
            current = None
    return blocks


class CheckerAssertions(unittest.TestCase):
    def run_checker(self, args, repo):
        before = git_status(repo)
        result = subprocess.run(args, cwd=PROJECT, env=checker_env(),
                                capture_output=True, text=True)
        self.assertEqual(git_status(repo), before, "Checker changed the target repository.")
        self.assertFalse(list(PROJECT.glob(".handoff-tmp.*")), "Temporary workspace left behind.")
        return result

    def assert_pass(self, result, required=REQUIRED):
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(result.stderr, "")
        self.assertIn("Result: PASS", result.stdout)
        blocks = findings(result.stdout)
        for name in required:
            self.assertEqual(blocks[name][0], "PASS", name)
        return blocks

    def assert_fail(self, result, path, in_commit, in_archive, required=REQUIRED):
        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        self.assertEqual(result.stderr, "")
        self.assertIn("Result: FAIL", result.stdout)
        blocks = findings(result.stdout)
        for name in required:
            self.assertEqual(blocks[name][0], "FAIL" if name == path else "PASS", name)
        location = next(line for line in blocks[path] if line.startswith("selected commit:"))
        committed, packaged = (part.split(": ", 1)[1] for part in location.split("; "))
        self.assertEqual(committed == "regular", in_commit, location)
        self.assertEqual(packaged == "regular", in_archive, location)
        self.assertTrue(any(line.startswith("Reason:") for line in blocks[path]))
        self.assertTrue(any(line.startswith("Suggested action:") for line in blocks[path]))
        return blocks

    def assert_error(self, result, *names):
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        self.assertEqual(result.stdout, "", "ERROR must not produce a PASS/FAIL report.")
        self.assertIn("ERROR:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        for name in names:
            self.assertIn(name, result.stderr)


class EvaluationFixtureTests(CheckerAssertions):
    """The eight docs/evaluation.md cases with their Section 3 expected outcomes."""

    @classmethod
    def setUpClass(cls):
        parent = PROJECT / ".scenario-runs"
        parent.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="eval fixtures ", dir=parent)
        cls.addClassCleanup(temporary.cleanup)
        manifest = fixtures.build_fixtures(Path(temporary.name) / "fixtures")
        cls.cases = {case["id"]: case for case in manifest["cases"]}

    def run_case(self, case_id):
        case = self.cases[case_id]
        return self.run_checker(shlex.split(case["checker_command"]), case["repo"])

    def test_generator_matches_reference_identifiers(self):
        self.assertEqual({case_id: case["commit"] for case_id, case in self.cases.items()},
                         REFERENCE_COMMITS)
        for case_id, case in self.cases.items():
            with self.subTest(case=case_id):
                if case_id in REFERENCE_ZIP_SHA256:
                    digest = hashlib.sha256(Path(case["zip"]).read_bytes()).hexdigest()
                    self.assertEqual(digest, REFERENCE_ZIP_SHA256[case_id])
                    self.assertEqual(case["zip_sha256"], REFERENCE_ZIP_SHA256[case_id])
                else:
                    self.assertIsNone(case["zip"])

    def test_case_01_complete_handoff_passes(self):
        self.assert_pass(self.run_case("case-01"))

    def test_case_02_untracked_required_file_fails_in_commit_and_archive(self):
        blocks = self.assert_fail(self.run_case("case-02"), "data/items.csv",
                                  in_commit=False, in_archive=False)
        self.assertIn('working tree: regular; Git status: "??"', blocks["data/items.csv"])

    def test_case_03_export_ignore_fails_in_archive_only(self):
        self.assert_fail(self.run_case("case-03"), "data/items.csv",
                         in_commit=True, in_archive=False)

    def test_case_04_unrelated_untracked_and_ignored_are_context(self):
        result = self.run_case("case-04")
        self.assert_pass(result)
        self.assertIn('Context: "notes/todo.txt"; Git status: "??"', result.stdout)
        self.assertIn('Context: "report.log"; Git status: "!!"', result.stdout)

    def test_case_05_parent_traversal_checklist_is_error(self):
        self.assert_error(self.run_case("case-05"), '"../data/items.csv"')

    def test_case_06_invalid_ref_is_error(self):
        self.assert_error(self.run_case("case-06"), "v1.0")

    def test_case_07_supplied_zip_omission_fails_in_archive_only(self):
        self.assert_fail(self.run_case("case-07"), "data/items.csv",
                         in_commit=True, in_archive=False)

    def test_case_08_invalid_zip_is_error(self):
        self.assert_error(self.run_case("case-08"), self.cases["case-08"]["zip"])


class CheckerEdgeCaseTests(CheckerAssertions):
    """Additional cases where the checker could still go wrong.

    Not covered by tests/test_python_checker.py; expected outcomes follow the
    proposal Section 3 rules (presence in commit and archive, not contents).
    """

    def setUp(self):
        parent = PROJECT / ".scenario-runs"
        parent.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="edge-case-", dir=parent)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        fixtures.git(self.repo, "init", "--quiet", "--template=", "--initial-branch=main")
        fixtures.write_files(self.repo, fixtures.PROJECT_FILES)

    def git(self, *args):
        return fixtures.git(self.repo, *args)

    def commit(self, *paths):
        self.git("add", "--", *paths)
        self.git("commit", "--quiet", "-m", "Edge case fixture")

    def check(self, *extra):
        return self.run_checker(["bash", str(CHECKER), "--repo", str(self.repo), *extra], self.repo)

    def test_ignored_required_file_never_committed_fails(self):
        # The proposal scenario's mechanism: required input ignored, so status shows !! not ??.
        fixtures.write_files(self.repo, {".gitignore": "*.csv\n"})
        self.commit(".gitignore", "README.md", "report.py", "handoff-check.json")
        blocks = self.assert_fail(self.check(), "data/items.csv", in_commit=False, in_archive=False)
        self.assertIn('working tree: regular; Git status: "!!"', blocks["data/items.csv"])

    def test_force_added_ignored_required_file_passes(self):
        fixtures.write_files(self.repo, {".gitignore": "*.csv\n"})
        self.git("add", "--force", "--", "data/items.csv")
        self.commit(".gitignore", "README.md", "report.py", "handoff-check.json")
        self.assert_pass(self.check())

    def test_staged_but_uncommitted_required_file_fails(self):
        self.commit("README.md", "report.py", "handoff-check.json")
        self.git("add", "--", "data/items.csv")
        blocks = self.assert_fail(self.check(), "data/items.csv", in_commit=False, in_archive=False)
        self.assertIn('working tree: regular; Git status: "A "', blocks["data/items.csv"])

    def test_executable_required_file_passes(self):
        self.git("add", "--", *fixtures.PROJECT_FILES)
        self.git("update-index", "--chmod=+x", "--", "report.py")
        self.git("commit", "--quiet", "-m", "Executable required file")
        self.assertTrue(self.git("ls-tree", "main", "report.py").startswith("100755 "))
        self.assert_pass(self.check())

    def test_locally_modified_required_file_still_passes(self):
        self.commit(*fixtures.PROJECT_FILES)
        (self.repo / "README.md").write_bytes(b"Edited after the selected commit.\n")
        blocks = self.assert_pass(self.check())
        self.assertIn('working tree: regular; Git status: " M"', blocks["README.md"])

    def test_zero_byte_required_file_passes(self):
        (self.repo / "data" / "items.csv").write_bytes(b"")
        self.commit(*fixtures.PROJECT_FILES)
        self.assert_pass(self.check())

    def test_non_ascii_required_name_passes(self):
        required = ["README.md", "data/données.csv"]
        fixtures.write_files(self.repo, {"data/données.csv": "item,quantity\n",
                                         "handoff-check.json": json.dumps({"required_files": required})})
        self.commit("README.md", "data/données.csv", "handoff-check.json")
        self.assert_pass(self.check(), required)

    def test_legacy_code_page_zip_names_are_matched(self):
        # Older Windows archivers store names in code page 437 without the UTF-8 flag.
        required = ["README.md", "data/données.csv"]
        fixtures.write_files(self.repo, {"data/données.csv": "item,quantity\n",
                                         "handoff-check.json": json.dumps({"required_files": required})})
        self.commit("README.md", "data/données.csv", "handoff-check.json")
        archive = self.root / "legacy.zip"
        archive.write_bytes(legacy_zip({"README.md": "x", "data/données.csv": "x",
                                        "notes/café.txt": "unrelated"}))
        with zipfile.ZipFile(archive) as package:
            self.assertFalse(any(info.flag_bits & 0x800 for info in package.infolist()))
        self.assert_pass(self.check("--zip", str(archive)), required)

    def test_non_utf8_untracked_name_is_context_only(self):
        try:
            with open(os.path.join(os.fsencode(self.repo), b"notes-\xe9.txt"), "wb") as file:
                file.write(b"not required\n")
        except OSError as exc:
            self.skipTest(f"File system rejects non-UTF-8 names: {exc}")
        self.commit(*fixtures.PROJECT_FILES)
        result = self.check()
        self.assert_pass(result)
        self.assertIn("Other Git status paths: 1", result.stdout)

    def test_empty_supplied_zip_fails_not_errors(self):
        self.commit(*fixtures.PROJECT_FILES)
        archive = self.root / "empty.zip"
        with zipfile.ZipFile(archive, "w"):
            pass
        result = self.check("--zip", str(archive))
        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        for name in REQUIRED:
            self.assertIn("selected commit: regular; ZIP: missing", findings(result.stdout)[name])

    def test_submodule_gitlink_does_not_satisfy_regular_file(self):
        required = ["README.md", "vendor/lib"]
        fixtures.write_files(self.repo, {"handoff-check.json": json.dumps({"required_files": required})})
        self.git("update-index", "--add", "--cacheinfo",
                 "160000,1111111111111111111111111111111111111111,vendor/lib")
        self.commit("README.md", "handoff-check.json")
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        block = findings(result.stdout)["vendor/lib"]
        self.assertEqual(block[0], "FAIL")
        self.assertTrue(any(line.startswith("selected commit: submodule;") for line in block), block)

    def test_unborn_head_is_error(self):
        # A freshly initialised repository with files but no commit yet.
        self.assert_error(self.check(), "HEAD")


def legacy_zip(files):
    """Build a ZIP whose non-ASCII names are code page 437 bytes with no UTF-8 flag."""
    encoded = {}
    with tempfile.SpooledTemporaryFile() as buffer:
        with zipfile.ZipFile(buffer, "w") as archive:
            for index, (name, text) in enumerate(files.items()):
                raw = name.encode("cp437")
                # zipfile always flags non-ASCII names as UTF-8, so write an
                # ASCII placeholder of the same length and patch the bytes after.
                placeholder = f"#{index}#".ljust(len(raw), "Q").encode("ascii")
                encoded[placeholder] = raw
                archive.writestr(placeholder.decode("ascii"), text)
        buffer.seek(0)
        data = buffer.read()
    for placeholder, raw in encoded.items():
        if placeholder != raw:
            assert data.count(placeholder) == 2, "placeholder must appear in local and central headers"
            data = data.replace(placeholder, raw)
    return data


if __name__ == "__main__":
    unittest.main()
