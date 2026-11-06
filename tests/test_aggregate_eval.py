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

HEADER = ("case,method,order,recorded_verdict,expected_verdict,analysis_verdict,"
          "commands,reconstructed_judgements,time_s,flags")
DIAG_HEADER = "member,case,method,missing_path_or_invalid_input,where_absent,next_action"
GOOD_DIAG = {
    "case-02": ("data/items.csv", "both", "commit it, rebuild ZIP"),
    "case-03": ("data/items.csv", "archive only", "remove export-ignore, rebuild ZIP"),
    "case-07": ("data/items.csv", "archive", "rebuild ZIP"),
    "case-05": ("../data/items.csv", "N/A", "fix checklist entry"),
    "case-06": ("v1.0", "N/A", "create the tag"),
    "case-08": ("handoff.zip", "N/A", "re-create the archive"),
}


def full_rows(time_manual=40, time_checker=30):
    """A complete, valid member: 8 cases x 2 methods, every verdict correct."""
    rows = {}
    for case, verdict in agg.EXPECTED_VERDICT.items():
        rows[(case, "manual")] = [case, "manual", "1st", verdict, verdict, verdict,
                                  "6", "18", str(time_manual), ""]
        rows[(case, "checker")] = [case, "checker", "2nd", verdict, verdict, verdict,
                                   "2", "2", str(time_checker), ""]
    return rows


def write_member(root, name, rows, diag=None):
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    lines = [HEADER] + [",".join(r) for r in rows]
    (d / "results-analysis.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if diag is not None:
        dl = [DIAG_HEADER] + [",".join([name, *r]) for r in diag]
        (d / "results.csv").write_text("\n".join(dl) + "\n", encoding="utf-8")


def full_diag(rows):
    out = []
    for case, method in rows:
        path, where, action = GOOD_DIAG.get(case, ("", "none", "none"))
        out.append([case, method, path, where, action])
    return out


class AggregateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def load(self, **kw):
        return agg.load_all(self.root, set(), **kw)

    def assertInputError(self, fragment, **kw):
        with self.assertRaises(agg.InputError) as cm:
            self.load(**kw)
        self.assertIn(fragment, str(cm.exception))

    # --- valid input -------------------------------------------------------

    def test_complete_member_summarises(self):
        rows = full_rows()
        write_member(self.root, "a", rows.values(), full_diag(rows))
        table = "\n".join(agg.report_table(self.load()))
        self.assertIn("| Correct verdicts | 8/8 | 8/8 |", table)
        self.assertIn("| FAIL diagnoses with path, location and action | 3/3 | 3/3 |", table)
        self.assertIn("| ERROR runs naming the invalid input | 3/3 | 3/3 |", table)
        self.assertIn("| False FAIL on unrelated files | 0/1 | 0/1 |", table)

    def test_accuracy_uses_analysis_verdict_and_reports_recorded_separately(self):
        rows = full_rows()
        rows[("case-05", "checker")][3] = "FAIL"      # recorded FAIL, log ERROR
        rows[("case-05", "manual")][3] = "FAIL"       # misclassified
        rows[("case-05", "manual")][5] = "FAIL"
        write_member(self.root, "a", rows.values())
        text = agg.report(self.load(), set())
        self.assertIn("| manual | 8 | 7/8 | 7/8 |", text)
        self.assertIn("| checker | 8 | 8/8 | 7/8 |", text)
        self.assertIn("transcription error (corrected from log)", text)
        self.assertIn("misclassification", text)

    def test_norm_where_accepts_member_spellings(self):
        for text, want in [("both", "both"), ("commit and archive", "both"),
                           ("archive only", "archive"), ("archive", "archive"),
                           ("commit", "commit"), ("none", ""), ("N/A", "")]:
            self.assertEqual(agg.norm_where(text), want, text)

    def test_incomplete_diagnosis_counts_as_not_complete(self):
        rows = full_rows()
        diag = full_diag(rows)
        for d in diag:
            if d[0] == "case-02" and d[1] == "checker":
                d[3] = "archive only"                 # wrong location
        write_member(self.root, "a", rows.values(), diag)
        table = "\n".join(agg.report_table(self.load()))
        self.assertIn("| FAIL diagnoses with path, location and action | 3/3 | 2/3 |", table)

    def test_diagnosis_is_na_without_results_csv(self):
        write_member(self.root, "a", full_rows().values())
        table = "\n".join(agg.report_table(self.load()))
        self.assertIn("| FAIL diagnoses with path, location and action | n/a | n/a |", table)

    # --- validation (MR !17 review) ----------------------------------------

    def test_duplicate_row_is_rejected(self):
        rows = list(full_rows().values())
        rows.append(list(rows[0]))
        write_member(self.root, "a", rows)
        self.assertInputError("duplicate row for case-01 manual")

    def test_missing_row_is_rejected(self):
        rows = full_rows()
        del rows[("case-03", "checker")]
        write_member(self.root, "a", rows.values())
        self.assertInputError("a case-03 checker")

    def test_missing_row_allowed_only_when_requested_and_labelled(self):
        rows = full_rows()
        del rows[("case-03", "checker")]
        write_member(self.root, "a", rows.values())
        loaded = self.load(allow_incomplete=True)
        self.assertIn("**INCOMPLETE: 1 run(s) missing: a case-03 checker**",
                      agg.report(loaded, set()))

    def test_missing_diagnostic_row_is_rejected(self):
        rows = full_rows()
        diag = [d for d in full_diag(rows) if not (d[0] == "case-02" and d[1] == "manual")]
        write_member(self.root, "a", rows.values(), diag)
        self.assertInputError("no diagnostic row for case-02 manual")

    def test_duplicate_diagnostic_row_is_rejected(self):
        rows = full_rows()
        diag = full_diag(rows)
        diag.append(list(diag[0]))
        write_member(self.root, "a", rows.values(), diag)
        self.assertInputError("duplicate row for case-01 manual")

    def test_bad_values_are_rejected(self):
        cases = [
            (6, "-1", "commands must not be negative"),
            (7, "2.5", "reconstructed_judgements must be a whole number"),
            (8, "nan", "time_s must be a finite positive number"),
            (8, "inf", "time_s must be a finite positive number"),
            (8, "0", "time_s must be a finite positive number"),
            (5, "MAYBE", "analysis_verdict must be PASS, FAIL or ERROR"),
            (4, "FAIL", "expected_verdict for case-01 is PASS"),
            (0, "case-09", "unknown case"),
        ]
        for col, value, fragment in cases:
            with self.subTest(value=value):
                for p in self.root.iterdir():
                    for f in p.iterdir():
                        f.unlink()
                    p.rmdir()
                rows = full_rows()
                rows[("case-01", "manual")][col] = value
                write_member(self.root, "a", rows.values())
                self.assertInputError(fragment)

    def test_missing_column_is_input_error(self):
        d = self.root / "a"
        d.mkdir()
        (d / "results-analysis.csv").write_text("case,method\ncase-01,manual\n", encoding="utf-8")
        self.assertInputError("missing column")

    def test_no_inputs_returns_exit_2(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(agg.main(["--root", str(self.root)]), 2)
        self.assertIn("no */results-analysis.csv", err.getvalue())

    def test_flags_column_optional(self):
        d = self.root / "a"
        d.mkdir()
        lines = ["case,method,recorded_verdict,expected_verdict,analysis_verdict,"
                 "commands,reconstructed_judgements,time_s"]
        lines += [f"{c},{m},{v},{v},{v},2,2,30"
                  for c, v in agg.EXPECTED_VERDICT.items() for m in ("manual", "checker")]
        (d / "results-analysis.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.assertTrue(all(r.flags == () for r in self.load()))

    # --- flagged pairs -----------------------------------------------------

    def test_one_sided_flag_drops_the_whole_pair(self):
        rows = full_rows()
        rows[("case-01", "manual")][9] = "time-corrected"   # checker side not flagged
        write_member(self.root, "a", rows.values())
        loaded = self.load()
        clean = agg.unflagged_pairs(loaded)
        self.assertNotIn(("a", "case-01"), {(r.member, r.case) for r in clean})
        self.assertEqual(len(clean), 14)
        methods = [r.method for r in clean]
        self.assertEqual(methods.count("manual"), methods.count("checker"))
        self.assertIn("1 flagged; 2 rows in flagged pairs", agg.report(loaded, set()))

    def test_exclude_member(self):
        write_member(self.root, "a", full_rows(30, 20).values())
        write_member(self.root, "b", full_rows(90, 60).values())
        rows = agg.load_all(self.root, {"b"})
        self.assertEqual({r.member for r in rows}, {"a"})

    # --- reproducibility ---------------------------------------------------

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
