#!/usr/bin/env python3
"""Aggregate per-member evaluation results into the summary tables for evaluation.md §8/§9.

Input:  docs/evaluation-runs/<member>/results-analysis.csv (one directory per member).
Output: Markdown tables on stdout (or --out FILE).

Each results-analysis.csv must contain at least:
    case, method, expected_verdict, analysis_verdict, recorded_verdict,
    commands, reconstructed_judgements, time_s
Optional column:
    flags   semicolon-separated labels (e.g. "ai-assisted;time-corrected").
            Rows with any flag are dropped in the "excluding flagged rows" view.

Use --exclude-member NAME (repeatable) for a sensitivity check without that member.
Standard library only; requires Python 3.12 like the rest of the project.
"""

from __future__ import annotations

import argparse
import csv
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

    @property
    def correct(self) -> bool:
        return self.analysis == self.expected

    @property
    def recorded_correct(self) -> bool:
        return self.recorded == self.expected


class InputError(Exception):
    pass


def load_member(path: Path) -> list[Row]:
    member = path.parent.name
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise InputError(f"{path}: missing column(s): {', '.join(missing)}")
        rows = []
        for lineno, raw in enumerate(reader, start=2):
            method = raw["method"].strip().lower()
            if method not in METHODS:
                raise InputError(f"{path}:{lineno}: unknown method {raw['method']!r}")
            try:
                rows.append(
                    Row(
                        member=member,
                        case=raw["case"].strip(),
                        method=method,
                        expected=raw["expected_verdict"].strip().upper(),
                        analysis=raw["analysis_verdict"].strip().upper(),
                        recorded=raw["recorded_verdict"].strip().upper(),
                        commands=int(raw["commands"]),
                        judgements=int(raw["reconstructed_judgements"]),
                        time_s=float(raw["time_s"]),
                        flags=tuple(
                            f.strip() for f in (raw.get("flags") or "").split(";") if f.strip()
                        ),
                    )
                )
            except ValueError as exc:
                raise InputError(f"{path}:{lineno}: {exc}") from exc
    return rows


def load_all(root: Path, exclude: set[str]) -> list[Row]:
    files = sorted(root.glob("*/results-analysis.csv"))
    if not files:
        raise InputError(f"no */results-analysis.csv found under {root}")
    rows: list[Row] = []
    for f in files:
        if f.parent.name not in exclude:
            rows.extend(load_member(f))
    return rows


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


def report(rows: list[Row], excluded: set[str]) -> str:
    members = sorted({r.member for r in rows})
    flagged = [r for r in rows if r.flags]
    clean = [r for r in rows if not r.flags]
    lines = [
        "# Evaluation summary (generated by scripts/aggregate_eval.py)",
        "",
        f"Members included: {', '.join(members) or 'none'}",
    ]
    if excluded:
        lines.append(f"Members excluded: {', '.join(sorted(excluded))}")
    lines += [
        f"Rows: {len(rows)} ({len(flagged)} flagged)",
        "",
        "## By method — all rows",
        "",
        *method_table(rows),
        "",
        "## By method — excluding flagged rows",
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
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path("docs/evaluation-runs"),
                    help="directory containing one sub-directory per member")
    ap.add_argument("--exclude-member", action="append", default=[], metavar="NAME",
                    help="leave a member out (sensitivity check); repeatable")
    ap.add_argument("--out", type=Path, help="write Markdown here instead of stdout")
    args = ap.parse_args(argv)
    excluded = set(args.exclude_member)
    try:
        rows = load_all(args.root, excluded)
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    text = report(rows, excluded)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
