#!/usr/bin/env python3
"""Aggregate per-member evaluation results into the summary tables for evaluation.md §8/§9.

Input:  docs/evaluation-runs/<member>/results-analysis.csv (one directory per member).
Output: Markdown tables on stdout (or --out FILE).

Each results-analysis.csv must contain at least:
    case, method, expected_verdict, analysis_verdict, recorded_verdict,
    commands, reconstructed_judgements, time_s
Optional column:
    flags   semicolon-separated labels (e.g. "ai-assisted;time-corrected").
            The "excluding flagged pairs" view drops BOTH methods of a member's
            case when either row is flagged, so manual and checker stay paired.

Input is validated before anything is computed: each member file must hold
exactly the 16 case x method rows once each, expected verdicts must match
evaluation.md §3, verdicts must be PASS/FAIL/ERROR, counts must be
non-negative integers and times finite positive numbers. If results.csv is
present it must have a diagnostic row for every analysis row. Any violation
is an ERROR (exit 2), not a silently different table. --allow-incomplete
accepts missing rows (still rejecting duplicates and bad values) and labels
the output INCOMPLETE.

If the member directory also holds the original results.csv, its diagnostic
fields (missing_path_or_invalid_input, where_absent, next_action) are joined by
case and method to compute the diagnosis measures (evaluation.md §8.4).

Use --exclude-member NAME (repeatable) for a sensitivity check without that member.
Use --repro DIR_A DIR_B to compare two scripts/repro_eval.sh outputs (§8.6).
Standard library only; requires Python 3.12 like the rest of the project.
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

REQUIRED = (
    "case",
    "method",
    "expected_verdict",
    "analysis_verdict",
    "recorded_verdict",
    "commands",
    "reconstructed_judgements",
    "time_s",
)
METHODS = ("manual", "checker")
CASES = tuple(f"case-{n:02d}" for n in range(1, 9))
VERDICTS = ("PASS", "FAIL", "ERROR")
# evaluation.md §3 expected verdicts.
EXPECTED_VERDICT = {"case-01": "PASS", "case-02": "FAIL", "case-03": "FAIL", "case-04": "PASS",
                    "case-05": "ERROR", "case-06": "ERROR", "case-07": "FAIL", "case-08": "ERROR"}

# evaluation.md §3: where the missing file is absent (FAIL cases), the invalid
# input that an ERROR diagnosis must name, and the context-only case.
EXPECTED_WHERE = {"case-02": "both", "case-03": "archive", "case-07": "archive"}
INVALID_INPUT = {"case-05": "../data/items.csv", "case-06": "v1.0", "case-08": "handoff.zip"}
MISSING_PATH = "data/items.csv"
CONTEXT_CASES = ("case-04",)
NO_ACTION = {"", "-", "none", "n/a", "na", "no action required"}


def norm_where(text: str) -> str:
    t = text.lower()
    if "both" in t or ("commit" in t and ("archive" in t or "zip" in t)):
        return "both"
    if "archive" in t or "zip" in t:
        return "archive"
    if "commit" in t:
        return "commit"
    return ""


def norm_case(text: str) -> str:
    t = text.strip().lower()
    digits = t[5:] if t.startswith("case-") else t
    if not (digits.isdigit() and len(digits) == 2 and f"case-{digits}" in CASES):
        raise ValueError(f"unknown case {text!r} (expected case-01 … case-08)")
    return f"case-{digits}"


def _nonneg_int(text: str, field: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise ValueError(f"{field} must be a whole number, got {text!r}") from None
    if value < 0:
        raise ValueError(f"{field} must not be negative, got {value}")
    return value


def _positive_time(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise ValueError(f"time_s must be a number, got {text!r}") from None
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"time_s must be a finite positive number, got {text!r}")
    return value


def _verdict(text: str, field: str) -> str:
    v = text.strip().upper()
    if v not in VERDICTS:
        raise ValueError(f"{field} must be PASS, FAIL or ERROR, got {text!r}")
    return v


@dataclass(frozen=True)
class Row:
    member: str
    case: str
    method: str
    expected: str
    analysis: str
    recorded: str
    commands: int
    judgements: int
    time_s: float
    flags: tuple[str, ...]
    order: str = ""
    missing: str | None = None   # None: no results.csv diagnostics available
    where: str | None = None
    action: str | None = None

    @property
    def correct(self) -> bool:
        return self.analysis == self.expected

    @property
    def recorded_correct(self) -> bool:
        return self.recorded == self.expected

    @property
    def has_diagnosis(self) -> bool:
        return self.missing is not None

    @property
    def fail_diagnosis_complete(self) -> bool:
        return (MISSING_PATH in (self.missing or "")
                and norm_where(self.where or "") == EXPECTED_WHERE.get(self.case)
                and (self.action or "").strip().lower() not in NO_ACTION)

    @property
    def names_invalid_input(self) -> bool:
        return INVALID_INPUT.get(self.case, "\0") in (self.missing or "")


class InputError(Exception):
    pass


def load_diagnostics(path: Path) -> dict[tuple[str, str], dict[str, str]] | None:
    """Rows of the member's results.csv keyed by (case, method); None if absent."""
    raw = path.parent / "results.csv"
    if not raw.exists():
        return None
    out: dict[tuple[str, str], dict[str, str]] = {}
    with raw.open(newline="", encoding="utf-8") as fh:
        for lineno, r in enumerate(csv.DictReader(fh), start=2):
            try:
                key = (norm_case(r.get("case") or ""), (r.get("method") or "").strip().lower())
            except ValueError as exc:
                raise InputError(f"{raw}:{lineno}: {exc}") from exc
            if key in out:
                raise InputError(f"{raw}:{lineno}: duplicate row for {key[0]} {key[1]}")
            out[key] = r
    return out


def load_member(path: Path) -> list[Row]:
    member = path.parent.name
    diag = load_diagnostics(path)
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise InputError(f"{path}: missing column(s): {', '.join(missing)}")
        rows = []
        seen: dict[tuple[str, str], int] = {}
        for lineno, raw in enumerate(reader, start=2):
            method = (raw["method"] or "").strip().lower()
            if method not in METHODS:
                raise InputError(f"{path}:{lineno}: unknown method {raw['method']!r}")
            try:
                case = norm_case(raw["case"] or "")
                expected = _verdict(raw["expected_verdict"] or "", "expected_verdict")
                if expected != EXPECTED_VERDICT[case]:
                    raise ValueError(f"expected_verdict for {case} is {EXPECTED_VERDICT[case]} "
                                     f"in evaluation.md §3, got {expected}")
            except ValueError as exc:
                raise InputError(f"{path}:{lineno}: {exc}") from exc
            if (case, method) in seen:
                raise InputError(f"{path}:{lineno}: duplicate row for {case} {method} "
                                 f"(first at line {seen[(case, method)]})")
            seen[(case, method)] = lineno
            d = None
            if diag is not None:
                d = diag.get((case, method))
                if d is None:
                    raise InputError(f"{path.parent / 'results.csv'}: no diagnostic row for "
                                     f"{case} {method}")
            try:
                rows.append(
                    Row(
                        member=member,
                        case=case,
                        method=method,
                        expected=expected,
                        analysis=_verdict(raw["analysis_verdict"] or "", "analysis_verdict"),
                        recorded=_verdict(raw["recorded_verdict"] or "", "recorded_verdict"),
                        commands=_nonneg_int(raw["commands"] or "", "commands"),
                        judgements=_nonneg_int(raw["reconstructed_judgements"] or "",
                                               "reconstructed_judgements"),
                        time_s=_positive_time(raw["time_s"] or ""),
                        flags=tuple(
                            f.strip() for f in (raw.get("flags") or "").split(";") if f.strip()
                        ),
                        order=(raw.get("order") or "").strip().lower(),
                        missing=None if d is None else d.get("missing_path_or_invalid_input", ""),
                        where=None if d is None else d.get("where_absent", ""),
                        action=None if d is None else d.get("next_action", ""),
                    )
                )
            except ValueError as exc:
                raise InputError(f"{path}:{lineno}: {exc}") from exc
    return rows


def missing_runs(rows: list[Row]) -> list[str]:
    """Member/case/method combinations absent from the loaded rows."""
    have = {(r.member, r.case, r.method) for r in rows}
    return [f"{m} {c} {meth}" for m in sorted({r.member for r in rows})
            for c in CASES for meth in METHODS if (m, c, meth) not in have]


def load_all(root: Path, exclude: set[str], allow_incomplete: bool = False) -> list[Row]:
    files = sorted(root.glob("*/results-analysis.csv"))
    if not files:
        raise InputError(f"no */results-analysis.csv found under {root}")
    rows: list[Row] = []
    for f in files:
        if f.parent.name not in exclude:
            rows.extend(load_member(f))
    gaps = missing_runs(rows)
    if gaps and not allow_incomplete:
        raise InputError(f"{len(gaps)} run(s) missing: {', '.join(gaps)} "
                         "(use --allow-incomplete to summarise anyway)")
    return rows


def unflagged_pairs(rows: list[Row]) -> list[Row]:
    """Drop both methods of a member's case if either row is flagged."""
    bad = {(r.member, r.case) for r in rows if r.flags}
    return [r for r in rows if (r.member, r.case) not in bad]


def _fmt(x: float) -> str:
    return f"{x:g}" if x == int(x) else f"{x:.1f}"


def method_table(rows: list[Row]) -> list[str]:
    out = [
        "| Method | Runs | Verdict correct (analysis) | Verdict correct (as recorded) "
        "| Median time (s) | Mean time (s) | Median commands | Median judgements |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for m in METHODS:
        rs = [r for r in rows if r.method == m]
        if not rs:
            out.append(f"| {m} | 0 | – | – | – | – | – | – |")
            continue
        n = len(rs)
        ok = sum(r.correct for r in rs)
        rec = sum(r.recorded_correct for r in rs)
        t = [r.time_s for r in rs]
        out.append(
            f"| {m} | {n} | {ok}/{n} | {rec}/{n} | {_fmt(statistics.median(t))} "
            f"| {_fmt(statistics.mean(t))} | {_fmt(statistics.median(r.commands for r in rs))} "
            f"| {_fmt(statistics.median(r.judgements for r in rs))} |"
        )
    return out


def case_table(rows: list[Row]) -> list[str]:
    out = [
        "| Case | Expected | Manual correct | Checker correct "
        "| Manual median time (s) | Checker median time (s) "
        "| Manual median judgements | Checker median judgements |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for case in sorted({r.case for r in rows}):
        cr = [r for r in rows if r.case == case]
        expected = "/".join(sorted({r.expected for r in cr}))
        cells = []
        for m in METHODS:
            rs = [r for r in cr if r.method == m]
            cells.append(f"{sum(r.correct for r in rs)}/{len(rs)}" if rs else "–")
        for key in ("time_s", "judgements"):
            for m in METHODS:
                vals = [getattr(r, key) for r in cr if r.method == m]
                cells.append(_fmt(statistics.median(vals)) if vals else "–")
        out.append(f"| {case} | {expected} | " + " | ".join(cells) + " |")
    return out


def errors_table(rows: list[Row]) -> list[str]:
    bad = [r for r in rows if not r.correct or not r.recorded_correct]
    if not bad:
        return ["No verdict errors."]
    out = [
        "| Member | Case | Method | Expected | Recorded | Analysis | Type |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in sorted(bad, key=lambda r: (r.member, r.case, r.method)):
        kind = "misclassification" if not r.correct else "transcription error (corrected from log)"
        out.append(
            f"| {r.member} | {r.case} | {r.method} | {r.expected} | {r.recorded} "
            f"| {r.analysis} | {kind} |"
        )
    return out


def _count(rows: list[Row], cases, test, needs_diagnosis: bool = False) -> str:
    rs = [r for r in rows if r.case in cases]
    if needs_diagnosis:
        rs = [r for r in rs if r.has_diagnosis]
    if not rs:
        return "n/a" if needs_diagnosis else "–"
    return f"{sum(test(r) for r in rs)}/{len(rs)}"


def _median_split(rs: list[Row]) -> str:
    if not rs:
        return "–"
    first = [r.time_s for r in rs if r.order.startswith("1")]
    second = [r.time_s for r in rs if r.order.startswith("2")]
    parts = [_fmt(statistics.median(x)) if x else "–" for x in (first, second)]
    return f"{_fmt(statistics.median(r.time_s for r in rs))} ({parts[0]} / {parts[1]})"


def report_table(rows: list[Row], repro: str | None = None) -> list[str]:
    """The Section 3 table of the final report, one row per measure."""
    by = {m: [r for r in rows if r.method == m] for m in METHODS}
    fail_cases, error_cases = tuple(EXPECTED_WHERE), tuple(INVALID_INPUT)

    def cell(m: str, kind: str) -> str:
        rs = by[m]
        if not rs:
            return "–"
        if kind == "correct":
            return f"{sum(r.correct for r in rs)}/{len(rs)}"
        if kind == "false_fail":
            return _count(rs, CONTEXT_CASES, lambda r: r.analysis == "FAIL")
        if kind == "fail_diag":
            return _count(rs, fail_cases, lambda r: r.fail_diagnosis_complete, True)
        if kind == "error_named":
            return _count(rs, error_cases, lambda r: r.names_invalid_input, True)
        if kind == "commands":
            return _fmt(statistics.median(r.commands for r in rs))
        if kind == "judgements":
            return _fmt(statistics.median(r.judgements for r in rs))
        if kind == "time":
            return _median_split(rs)
        raise ValueError(kind)

    labels = [
        ("Correct verdicts", "correct"),
        ("False FAIL on unrelated files", "false_fail"),
        ("FAIL diagnoses with path, location and action", "fail_diag"),
        ("ERROR runs naming the invalid input", "error_named"),
        ("Commands per case (median)", "commands"),
        ("Judgements per case (median)", "judgements"),
        ("Time per case, s (median; first / second position)", "time"),
    ]
    out = ["| Measure | Manual baseline | Handoff Check |", "|---|---|---|"]
    out += [f"| {label} | {cell('manual', k)} | {cell('checker', k)} |" for label, k in labels]
    out.append(f"| Identical CI and unit-server results (of 8) | — | {repro or 'not run'} |")
    return out


def compare_repro(a: Path, b: Path) -> tuple[str, list[str]]:
    """Compare two repro_eval.sh output directories case by case (§8.6)."""
    for d in (a, b):
        if not (d / "summary.csv").exists():
            raise InputError(f"{d}: no summary.csv (not a repro_eval.sh output)")
    lines = [
        f"A: {a}", f"B: {b}", "",
        "| Case | Exit A | Exit B | Same fixture commit | stdout identical | stderr identical (normalised) |",
        "|---|---|---|---|---|---|",
    ]
    with (a / "summary.csv").open(encoding="utf-8") as fa, (b / "summary.csv").open(encoding="utf-8") as fb:
        sa = {r["case"]: r for r in csv.DictReader(fa)}
        sb = {r["case"]: r for r in csv.DictReader(fb)}
    same = 0
    for case in sorted(set(sa) | set(sb)):
        ra, rb = sa.get(case), sb.get(case)
        if ra is None or rb is None:
            lines.append(f"| {case} | {ra and ra['exit'] or '–'} | {rb and rb['exit'] or '–'} | – | – | – |")
            continue
        commit = (ra["commit"], ra["zip_sha256"]) == (rb["commit"], rb["zip_sha256"])
        out_eq = (a / f"{case}.stdout").read_bytes() == (b / f"{case}.stdout").read_bytes()
        err_eq = (a / f"{case}.stderr").read_bytes() == (b / f"{case}.stderr").read_bytes()
        ok = commit and out_eq and err_eq and ra["exit"] == rb["exit"]
        same += ok
        yn = lambda v: "yes" if v else "**no**"
        lines.append(f"| {case} | {ra['exit']} | {rb['exit']} | {yn(commit)} | {yn(out_eq)} | {yn(err_eq)} |")
    return f"{same}/{len(set(sa) | set(sb))}", lines


def report(rows: list[Row], excluded: set[str], repro: tuple[str, list[str]] | None = None) -> str:
    members = sorted({r.member for r in rows})
    flagged = [r for r in rows if r.flags]
    clean = unflagged_pairs(rows)
    gaps = missing_runs(rows)
    lines = [
        "# Evaluation summary (generated by scripts/aggregate_eval.py)",
        "",
    ]
    if gaps:
        lines += [f"**INCOMPLETE: {len(gaps)} run(s) missing: {', '.join(gaps)}**", ""]
    lines += [f"Members included: {', '.join(members) or 'none'}"]
    if excluded:
        lines.append(f"Members excluded: {', '.join(sorted(excluded))}")
    lines += [
        f"Rows: {len(rows)} ({len(flagged)} flagged; {len(rows) - len(clean)} rows "
        "in flagged pairs)",
        "",
        "## Report Section 3 table — all rows",
        "",
        *report_table(rows, repro[0] if repro else None),
        "",
        "## Report Section 3 table — excluding flagged pairs",
        "",
        *(report_table(clean, repro[0] if repro else None) if flagged
          else ["No flagged rows; identical to the table above."]),
        "",
        "## By method — all rows",
        "",
        *method_table(rows),
        "",
        "## By method — excluding flagged pairs",
        "",
        *(method_table(clean) if flagged else ["No flagged rows; identical to the table above."]),
        "",
        "## By case — all rows",
        "",
        *case_table(rows),
        "",
        "## Verdict errors",
        "",
        *errors_table(rows),
        "",
    ]
    if flagged:
        lines += ["## Flagged rows", "", "| Member | Case | Method | Flags |", "|---|---|---|---|"]
        lines += [f"| {r.member} | {r.case} | {r.method} | {'; '.join(r.flags)} |" for r in flagged]
        lines.append("")
    if repro:
        lines += ["## Reproducibility (§8.6)", "", *repro[1], ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path("docs/evaluation-runs"),
                    help="directory containing one sub-directory per member")
    ap.add_argument("--exclude-member", action="append", default=[], metavar="NAME",
                    help="leave a member out (sensitivity check); repeatable")
    ap.add_argument("--repro", nargs=2, type=Path, metavar=("DIR_A", "DIR_B"),
                    help="compare two scripts/repro_eval.sh output directories")
    ap.add_argument("--allow-incomplete", action="store_true",
                    help="summarise even if some runs are missing (output is labelled INCOMPLETE)")
    ap.add_argument("--out", type=Path, help="write Markdown here instead of stdout")
    args = ap.parse_args(argv)
    excluded = set(args.exclude_member)
    try:
        rows = load_all(args.root, excluded, args.allow_incomplete)
        repro = compare_repro(*args.repro) if args.repro else None
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    text = report(rows, excluded, repro)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
