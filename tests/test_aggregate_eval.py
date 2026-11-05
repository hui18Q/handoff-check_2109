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

    def test_norm_where_accepts_member_spellings(self):
        for text, want in [("both", "both"), ("commit and archive", "both"),
                           ("archive only", "archive"), ("archive", "archive"),
                           ("commit", "commit"), ("none", ""), ("N/A", "")]:
            self.assertEqual(agg.norm_where(text), want, text)

    def test_report_table_uses_results_csv_diagnostics(self):
        write_member(self.root, "a",
                     "case-02,manual,FAIL,FAIL,FAIL,6,19,40,\n"
                     "case-02,checker,FAIL,FAIL,FAIL,2,4,20,\n"
                     "case-06,manual,FAIL,ERROR,FAIL,1,3,30,\n"
                     "case-04,checker,FAIL,PASS,FAIL,2,3,20,\n")
        (self.root / "a" / "results.csv").write_text(
            "member,case,method,missing_path_or_invalid_input,where_absent,next_action\n"
            "a,case-02,manual,data/items.csv,commit and archive,commit it\n"
            "a,case-02,checker,data/items.csv,archive only,commit it\n"
            "a,case-06,manual,ref v1.0,N/A,create the tag\n"
            "a,case-04,checker,,N/A,None\n", encoding="utf-8")
        table = "\n".join(agg.report_table(agg.load_all(self.root, set())))
        self.assertIn("| FAIL diagnoses with path, location and action | 1/1 | 0/1 |", table)
        self.assertIn("| ERROR runs naming the invalid input | 1/1 | n/a |", table)
        self.assertIn("| False FAIL on unrelated files | – | 1/1 |", table)

    def test_diagnosis_is_na_without_results_csv(self):
        write_member(self.root, "a", "case-02,manual,FAIL,FAIL,FAIL,6,19,40,\n")
        table = "\n".join(agg.report_table(agg.load_all(self.root, set())))
        self.assertIn("| FAIL diagnoses with path, location and action | n/a | – |", table)

    def _repro_dir(self, name, exit_code, stdout):
        d = self.root / name
        d.mkdir()
        (d / "summary.csv").write_text(
            f"case,commit,zip_sha256,exit,verdict\ncase-01,abc,-,{exit_code},PASS\n",
            encoding="utf-8")
        (d / "case-01.stdout").write_text(stdout, encoding="utf-8")
        (d / "case-01.stderr").write_text("", encoding="utf-8")
        return d

    def test_compare_repro_identical_and_different(self):
        a = self._repro_dir("ra", 0, "Result: PASS\n")
        b = self._repro_dir("rb", 0, "Result: PASS\n")
        c = self._repro_dir("rc", 0, "Result: PASS (changed)\n")
        self.assertEqual(agg.compare_repro(a, b)[0], "1/1")
        summary, lines = agg.compare_repro(a, c)
        self.assertEqual(summary, "0/1")
        self.assertIn("**no**", "\n".join(lines))

    def test_compare_repro_rejects_non_output_dir(self):
        with self.assertRaises(agg.InputError):
            agg.compare_repro(self.root, self.root)


if __name__ == "__main__":
    unittest.main()
