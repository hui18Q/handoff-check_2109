# Lu Wenxi — evaluation records and qualifications

Measured on 5 November 2026; this explanatory record was added on
6 November 2026.

## Files and version

- `results.csv` contains the sixteen participant records, including later
  documented revisions. It is not an unchanged copy of the initial CSV.
- `logs/case-NN-manual.log` and `logs/case-NN-checker.log` map to the
  corresponding case and method rows. All sixteen raw logs are retained.
- The original CSV and logs were committed as `7b1f6c0`.
  Revision `d3ed67f` added reconstructed judgement counts and clarified
  timing records; MR !14 records their independent review.
- `results-analysis.csv` is the derived analysis input introduced through
  MR !17. It identifies the four time-corrected observations.
- All measured checker runs assessed frozen source commit
  `71d7472d7e920b2bba64327e9b69c3c18ecacd60`, following Lu's assigned
  case and method order in `docs/evaluation.md` Section 7.

## Judgements and AI involvement

Judgement counts were reconstructed retrospectively from the logs under
the J/K definitions in protocol Sections 4.3 and 5. They were not tallied
during measurement, and no additional unlogged checks were assumed.
They describe procedure-defined judgement points, not directly measured
cognitive effort.

ChatGPT was used for preparation before timing. Lu confirms that the
timed procedures, output interpretation, verdicts and diagnostic fields
were completed independently before stopping the timer. Later AI-assisted
review and report drafting are separate activities.

## Duration corrections

| Run | Earlier recorded values (seconds) | Current value (seconds) |
|---|---|---|
| case-01 manual | 26, then 30 | 40 |
| case-01 checker | 15 | 25 |
| case-02 checker | 15 | 25 |
| case-02 manual | 28 | 38 |

The earlier values remain in the CSV notes and Git history. They are
recording history, not additional trials. Both methods of cases 01 and 02
are flagged `time-corrected`; excluding flagged pairs removes these two
member-case pairs together.

## Evidence limits

The logs support inspection of executed commands and terminal output.
They do not independently establish stopwatch endpoints or cognitive
judgement events. The raw logs were not rewritten to reflect CSV
corrections. Aggregate results and sensitivity views are documented in
`docs/evaluation.md` Section 8 and `docs/evaluation-runs/summary.md`.
