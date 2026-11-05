"""Unit tests for scripts/aggregate_eval.py (stdlib unittest)."""

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("aggregate_eval", ROOT / "scripts" / "aggregate_eval.py")
agg = importlib.util.module_from_spec(_spec)
sys.modules["aggregate_eval"] = agg
_spec.loader.exec_module(agg)

HEADER = ("case,method,recorded_verdict,expected_verdict,analysis_verdict,"
          "commands,reconstructed_judgements,time_s,flags\n")


def write_member(root: Path, name: str, body: str) -> None:
    d = root / name
    d.mkdir(parents=True)
    (d / "results-analysis.csv").write_text(HEADER + body, encoding="utf-8")


class AggregateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_accuracy_uses_analysis_verdict_and_reports_recorded_separately(self):
        write_member(self.root, "a",
                     "case-05,checker,FAIL,ERROR,ERROR,2,2,30,\n"
                     "case-05,manual,FAIL,ERROR,FAIL,6,19,40,\n")
        text = agg.report(agg.load_all(self.root, set()), set())
        self.assertIn("| manual | 1 | 0/1 | 0/1 |", text)
        self.assertIn("| checker | 1 | 1/1 | 0/1 |", text)
        self.assertIn("transcription error (corrected from log)", text)
        self.assertIn("misclassification", text)

    def test_flagged_rows_dropped_in_clean_view(self):
        write_member(self.root, "a",
                     "case-01,manual,PASS,PASS,PASS,6,16,40,\n"
                     "case-01,manual,PASS,PASS,PASS,6,16,100,time-corrected\n")
        rows = agg.load_all(self.root, set())
        self.assertEqual(agg.method_table(rows)[2].split("|")[5].strip(), "70")
        clean = [r for r in rows if not r.flags]
        self.assertEqual(agg.method_table(clean)[2].split("|")[5].strip(), "40")
        self.assertIn("## Flagged rows", agg.report(rows, set()))

    def test_exclude_member(self):
        write_member(self.root, "a", "case-01,checker,PASS,PASS,PASS,2,1,30,\n")
        write_member(self.root, "b", "case-01,checker,PASS,PASS,PASS,2,1,90,\n")
        rows = agg.load_all(self.root, {"b"})
        self.assertEqual({r.member for r in rows}, {"a"})

    def test_missing_column_is_input_error(self):
        d = self.root / "a"
        d.mkdir()
        (d / "results-analysis.csv").write_text("case,method\ncase-01,manual\n", encoding="utf-8")
        with self.assertRaises(agg.InputError):
            agg.load_all(self.root, set())

    def test_no_inputs_returns_exit_2(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(agg.main(["--root", str(self.root)]), 2)
        self.assertIn("no */results-analysis.csv", err.getvalue())

    def test_flags_column_optional(self):
        d = self.root / "a"
        d.mkdir()
        (d / "results-analysis.csv").write_text(
            "case,method,recorded_verdict,expected_verdict,analysis_verdict,"
            "commands,reconstructed_judgements,time_s\n"
            "case-01,manual,PASS,PASS,PASS,6,16,40\n", encoding="utf-8")
        rows = agg.load_all(self.root, set())
        self.assertEqual(rows[0].flags, ())


if __name__ == "__main__":
    unittest.main()
