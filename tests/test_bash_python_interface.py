import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEST_DOUBLE = '''import argparse
import base64
import json
import os
from pathlib import Path
import sys
import zipfile

parser = argparse.ArgumentParser()
for name in ("repo", "commit", "checklist", "status-file", "tree-file", "archive"):
    parser.add_argument("--" + name, required=True)
args = parser.parse_args()
record = vars(args)
record["checklist_text"] = Path(args.checklist).read_text(encoding="utf-8")
record["status_b64"] = base64.b64encode(Path(args.status_file).read_bytes()).decode()
record["tree_b64"] = base64.b64encode(Path(args.tree_file).read_bytes()).decode()
with zipfile.ZipFile(args.archive) as archive:
    record["zip_names"] = archive.namelist()
    record["zip_readme"] = archive.read("README.md").decode()
Path(os.environ["HANDOFF_TEST_CAPTURE"]).write_text(json.dumps(record), encoding="utf-8")
code = int(os.environ["HANDOFF_TEST_EXIT"])
print(f"INTERFACE_TEST_DOUBLE exit={code}", file=sys.stderr if code >= 2 else sys.stdout)
sys.exit(code)
'''


class BashPythonInterfaceTests(unittest.TestCase):
    """Check Bash orchestration using an isolated Python test double."""

    def setUp(self):
        self.assertEqual(
            sys.version_info[:2], (3, 12), "Run with Python 3.12."
        )
        self.git_executable = shutil.which("git")
        self.bash_executable = shutil.which("bash")
        self.assertIsNotNone(self.git_executable, "Git is required.")
        self.assertIsNotNone(self.bash_executable, "Bash is required.")

        parent = PROJECT_ROOT / ".scenario-runs"
        parent.mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(
            prefix="bash-interface-", dir=parent
        )
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.tool = self.root / "tool with spaces"
        self.repo = self.root / "target with spaces"
        self.caller = self.root / "caller"

        for directory in (
            self.tool / "scripts",
            self.tool / "src",
            self.repo,
            self.caller,
        ):
            directory.mkdir(parents=True)

        self.script = self.tool / "scripts/handoff_check.sh"
        shutil.copy2(PROJECT_ROOT / "scripts/handoff_check.sh", self.script)
        self.checker = self.tool / "src/handoff_check.py"
        self.checker.write_text(TEST_DOUBLE, encoding="utf-8")
        self.capture = self.root / "capture.json"

        self.env = os.environ.copy()
        self.env["PATH"] = (
            str(Path(sys.executable).parent)
            + os.pathsep
            + self.env.get("PATH", "")
        )
        self.env["HANDOFF_TEST_CAPTURE"] = str(self.capture)

        for name in (
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_COMMON_DIR",
            "GIT_INDEX_FILE",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_OPTIONAL_LOCKS",
        ):
            self.env.pop(name, None)

        self.git("init", "-q")
        self.committed_checklist = '{"required_files":["README.md"]}\n'
        (self.repo / "handoff-check.json").write_text(
            self.committed_checklist, encoding="utf-8"
        )
        (self.repo / "README.md").write_text(
            "first commit\n", encoding="utf-8"
        )
        (self.repo / "tracked name.txt").write_text(
            "tracked\n", encoding="utf-8"
        )
        (self.repo / "line\nname.txt").write_text(
            "newline filename\n", encoding="utf-8"
        )
        (self.repo / ".gitignore").write_text(
            "ignored.txt\n", encoding="utf-8"
        )
        self.git("add", ".")
        self.commit("first fixture commit")
        self.selected_commit = self.git(
            "rev-parse", "HEAD"
        ).decode().strip()

        (self.repo / "README.md").write_text(
            "second commit\n", encoding="utf-8"
        )
        (self.repo / "handoff-check.json").write_text(
            '{"required_files":["README.md","tracked name.txt"]}\n',
            encoding="utf-8",
        )
        self.git("add", ".")
        self.commit("second fixture commit")

        (self.repo / "handoff-check.json").write_text(
            '{"required_files":["LOCAL_ONLY.txt"]}\n',
            encoding="utf-8",
        )
        (self.repo / "README.md").write_text(
            "local working content\n", encoding="utf-8"
        )
        self.git("add", "README.md")
        self.git("mv", "tracked name.txt", "renamed name.txt")
        (self.repo / "untracked\nfile.txt").write_text(
            "untracked\n", encoding="utf-8"
        )
        (self.repo / "ignored.txt").write_text(
            "ignored\n", encoding="utf-8"
        )

        unchanged = self.repo / "line\nname.txt"
        stat = unchanged.stat()
        os.utime(
            unchanged,
            ns=(stat.st_atime_ns, stat.st_mtime_ns - 2_000_000_000),
        )
        self.before = self.snapshot()

    def git(self, *args):
        return subprocess.run(
            [self.git_executable, "-C", str(self.repo), *args],
            env={**self.env, "GIT_OPTIONAL_LOCKS": "0"},
            check=True,
            capture_output=True,
        ).stdout

    def commit(self, message):
        self.git(
            "-c", "user.name=Handoff Fixture",
            "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", message,
        )

    def snapshot(self):
        return {
            str(path.relative_to(self.repo)): (
                path.read_bytes(),
                path.stat().st_mode,
                path.stat().st_mtime_ns,
            )
            for path in self.repo.rglob("*")
            if path.is_file()
        }

    def run_tool(self, *extra, code=0, ref=None):
        if self.capture.exists():
            self.capture.unlink()

        env = self.env.copy()
        env["HANDOFF_TEST_EXIT"] = str(code)
        result = subprocess.run(
            [
                self.bash_executable,
                str(self.script),
                "--repo", str(self.repo),
                "--ref", self.selected_commit if ref is None else ref,
                *extra,
            ],
            cwd=self.caller,
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertFalse(
            list(self.tool.glob(".handoff-tmp.*")),
            "Workspace was not cleaned.",
        )
        self.assertEqual(
            self.snapshot(), self.before, "Target repository changed."
        )
        return result

    def test_exit_codes_streams_and_evidence(self):
        for code in (0, 1, 2):
            with self.subTest(code=code):
                result = self.run_tool(code=code)
                self.assertEqual(result.returncode, code, result.stderr)

                message = f"INTERFACE_TEST_DOUBLE exit={code}\n"
                self.assertEqual(
                    result.stdout, message if code < 2 else ""
                )
                self.assertEqual(
                    result.stderr, message if code == 2 else ""
                )

                record = json.loads(
                    self.capture.read_text(encoding="utf-8")
                )
                for name in (
                    "repo", "checklist", "status_file",
                    "tree_file", "archive",
                ):
                    self.assertTrue(
                        Path(record[name]).is_absolute(), name
                    )

                self.assertEqual(record["repo"], str(self.repo))
                self.assertEqual(
                    record["commit"], self.selected_commit
                )
                self.assertEqual(
                    record["checklist_text"], self.committed_checklist
                )
                self.assertEqual(
                    base64.b64decode(record["status_b64"]),
                    self.git(
                        "status", "--porcelain=v1", "-z",
                        "--untracked-files=all", "--ignored",
                    ),
                )
                self.assertEqual(
                    base64.b64decode(record["tree_b64"]),
                    self.git(
                        "ls-tree", "-r", "-z", "--full-tree",
                        self.selected_commit,
                    ),
                )
                self.assertEqual(
                    record["zip_readme"], "first commit\n"
                )
                self.assertIn("line\nname.txt", record["zip_names"])
                self.assertEqual(
                    Path(record["checklist"]).parent.parent,
                    self.tool,
                )
                for name in (
                    "checklist", "status_file", "tree_file", "archive"
                ):
                    self.assertFalse(
                        Path(record[name]).exists(), name
                    )

    def test_supplied_zip_paths_and_preservation(self):
        supplied = self.caller / "supplied handoff.zip"
        supplied.write_bytes(
            self.git("archive", "--format=zip", self.selected_commit)
        )
        supplied.chmod(0o444)
        before = (
            supplied.read_bytes(),
            supplied.stat().st_mode,
            supplied.stat().st_mtime_ns,
        )

        for value in (str(supplied), supplied.name):
            with self.subTest(path=value):
                result = self.run_tool("--zip", value)
                self.assertEqual(
                    result.returncode, 0, result.stderr
                )
                record = json.loads(
                    self.capture.read_text(encoding="utf-8")
                )
                self.assertEqual(record["archive"], str(supplied))
                self.assertEqual(
                    (
                        supplied.read_bytes(),
                        supplied.stat().st_mode,
                        supplied.stat().st_mtime_ns,
                    ),
                    before,
                )

    def test_missing_checker_is_error(self):
        self.checker.unlink()
        result = self.run_tool()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn(
            "Python checker is missing or unreadable", result.stderr
        )
        self.assertFalse(self.capture.exists())

    def test_unsupported_checker_exit_is_error(self):
        result = self.run_tool(code=99)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("unsupported exit code: 99", result.stderr)

    def test_missing_supplied_zip_is_error(self):
        result = self.run_tool("--zip", "missing.zip")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn(
            "Supplied ZIP is not a readable file", result.stderr
        )
        self.assertFalse(self.capture.exists())

    def test_invalid_ref_is_error(self):
        result = self.run_tool(
            ref="refs/heads/__handoff_missing_ref__"
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("Ref does not resolve", result.stderr)
        self.assertFalse(self.capture.exists())


if __name__ == "__main__":
    unittest.main()
