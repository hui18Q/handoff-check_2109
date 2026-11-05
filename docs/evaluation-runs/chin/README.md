# Chin Wen Hui — measured runs: evidence map and deviations

This file explains `results.csv` and `logs/` in response to the MR !16 review.
`results.csv` and every raw log are unchanged; nothing below replaces a recorded value.

## 1. How the logs were recorded

- `logs/case-07-checker.log` started at 21:08:40 and was **never exited**, so it is a
  parent recording of the whole session from 21:08:40 onward. Every later run was a
  nested `script` session started inside it. Each nested run also has its own file.
- All times are from the `Script started/done` headers (UTC+08:00, 2026-11-05).
- Line numbers refer to the raw log as shown in a text editor (first line = 1). Use `cat` in a terminal to view the logs without control codes.
- `time_s` in `results.csv` was measured with a separate stopwatch (phone timer). The
  `Script started/done` times cover the whole recording session, including setup, reading,
  filling in the CSV and, in some runs, a delay before `exit` was typed, so session length
  is longer than `time_s` and should not be used as the measured time.

## 2. Actual execution sequence and CSV mapping

| Seq | Run | Evidence | Session start–end | CSV row |
|---|---|---|---|---|
| 1 | case-07 checker | parent log lines 2–21 | 21:08:40– | case-07 checker (50 s) |
| 2 | case-07 manual, attempt A | parent log lines 24–54 (its nested file was later overwritten) | before 21:17 | case-07 manual (40 s) — recorded before attempt B began |
| 3 | case-07 manual, attempt B (repeat run, also timed at 40 s; not used) | `case-07-manual.log`, parent lines 56–86 | 21:17:25–21:23:07 | not used — same 40 s, so the CSV value does not depend on which attempt is used |
| 4 | case-08 manual | `case-08-manual.log` | 21:23:13–21:25:33 | case-08 manual |
| 5 | case-08 checker | `case-08-checker.log` | 21:25:48–21:30:30 | case-08 checker |
| 6 | case-01 checker | `case-01-checker.log` | 21:30:33–21:32:04 | case-01 checker |
| 7 | case-01 manual | `case-01-manual.log` | 21:32:14–21:35:04 | case-01 manual |
| 8 | case-02 manual | `case-02-manual.log` | 21:35:18–21:36:38 | case-02 manual |
| 9 | case-06 manual (extra, out of order) | parent log lines 220–251 (its nested file was later overwritten) | ~21:36:40–21:37:50 | not used |
| 10 | case-02 checker | `case-02-checker.log` | 21:37:55–21:39:21 | case-02 checker |
| 11 | case-03 checker, attempt A | parent log lines 278–300 (its nested file was later overwritten) | after 21:39:21 | case-03 checker (31 s) |
| 12 | case-03 checker, attempt B (setup + exit only) | `case-03-checker.log` | 21:49:50–21:50:02 | not used |
| 13 | case-03 manual | `case-03-manual.log` | 21:50:09–21:51:15 | case-03 manual |
| 14 | case-04 manual | `case-04-manual.log` | 21:51:36–21:52:45 | case-04 manual |
| 15 | case-04 checker | `case-04-checker.log` | 21:53:11–21:54:44 | case-04 checker |
| 16 | case-05 checker | `case-05-checker.log` | 21:54:54–21:55:56 | case-05 checker |
| 17 | case-05 manual | `case-05-manual.log` | 21:56:24–21:57:40 | case-05 manual |
| 18 | case-06 manual | `case-06-manual.log` | 21:58:00–21:59:08 | case-06 manual |
| 19 | case-06 checker | `case-06-checker.log` | 21:59:25–22:00:21 | case-06 checker |

Additional exposure beyond the disclosed earlier attempt: case-07 manual was run twice,
case-03 checker was started twice, and case-06 manual was run once out of order before
its measured run.

## 3. Procedure deviations

1. **Manual commands were pasted as one block.** In all eight manual runs the logs show
   the full command list entered at once, so the §4.3 stop rules could not take effect
   (case-05 and case-06 ran all six commands). The step sheet used listed the commands as
   one copyable block, which contributed to this. Times and command counts are kept as
   measured; manual effort here reflects block execution plus reading, not step-by-step
   inspection.
2. **case-07 checker retry.** The recorded session contains a single, successful checker
   execution. The environment-variable error mentioned in the notes is not in the
   recording, so it occurred before `script` started and before timing; commands = 2
   reflects the timed run.
3. **Verdict recording for cases 05, 06 and 08.** Both methods were recorded as FAIL. The
   participant classified cases 05, 06 and 08 as FAIL based on the terminal output.
   - Checker rows: the recorded exit code is 2 and the log shows ERROR, so FAIL is a
     transcription error.
   - Manual rows: FAIL is the participant's judgement, which is the measured outcome. It is
     scored as a misclassification (expected ERROR), not corrected.

   `results.csv` is unchanged. `results-analysis.csv` (derived, not a measurement record)
   lists recorded vs expected verdicts, log exit codes and reconstructed judgement counts;
   checker rows use the log verdict and manual rows keep the recorded verdict.
4. **Judgement counts were estimates.** The recorded values used a fixed reference rather
   than a per-run tally. They are kept, and the table below gives counts reconstructed
   from the logs under §4.3/§5 for comparison with other members.

## 4. Judgement counts

"Reconstructed" counts the J/K points for the commands actually executed and the fields
actually recorded. "Reference" is the §4.4 procedure minimum.

| Run | Recorded (estimate) | Reconstructed (breakdown) | Reference |
|---|---|---|---|
| case-07 checker | 4 | 4 (K1+K2a+K2b+K2c) | 4 |
| case-07 manual | 19 | 19 (J1+J2+J3×3+J4×3+J6×3+J7+J8×3+J9+J10+J11+J12) | 19 |
| case-08 manual | 16 | 16 (J1+J2+J3×3+J4×3+J6×3+J7+J9+J10+J11+J12; archive unreadable, no J8) | 14 |
| case-08 checker | 4 | 2 (K1+K3) | 2 |
| case-01 checker | 4 | 1 (K1) | 1 |
| case-01 manual | 20 | 16 (J1+J2+J3×3+J4×3+J6×3+J7+J8×3+J9) | 16 |
| case-02 manual | 20 | 19 (as case-07 manual) | 19 |
| case-02 checker | 4 | 4 (K1+K2a+K2b+K2c) | 4 |
| case-03 checker | 4 | 4 (K1+K2a+K2b+K2c) | 4 |
| case-03 manual | 20 | 19 (as case-07 manual) | 19 |
| case-04 manual | 20 | 18 (J1+J2+J3×3+J4×3+J5×2+J6×3+J7+J8×3+J9) | 18 |
| case-04 checker | 4 | 3 (K1+K4×2) | 3 |
| case-05 checker | 4 | 2 (K1+K3) | 2 |
| case-05 manual | 17 | 19 (all six commands run: J1+J2+J3×3+J4×3+J6×3+J7+J8×3+J9+J10+J11+J12) | 7 |
| case-06 manual | 5 | 5 (J1+J9+J10+J11+J12; later commands produced no evaluable output) | 3 |
| case-06 checker | 4 | 2 (K1+K3) | 2 |

## 5. Frozen checker version

- During setup (outside the recorded sessions) `git -C ../checker-71d7472 rev-parse HEAD`
  printed `71d7472d7e920b2bba64327e9b69c3c18ecacd60`; that output was not logged.
- Every checker run in the logs is executed from `~/fit2109/checker-71d7472`.
- `frozen-checker-retrospective.txt` is a **retrospective** confirmation collected after
  measurement, not a measurement-time record.