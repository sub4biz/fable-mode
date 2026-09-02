# Fable skill benchmark — Claude Fable 5.1 — 2026-09-02

Question: does the fable-mode discipline (stage map → failable checks → self-critique,
briefed verbatim from `fable-fable`) change outcomes on Claude Fable 5.1?

**Answer: no measurable correctness delta. 16 paired runs, every cell 100/100. The skill
costs ~1.1× tokens and ~1.5–2.3× wall time on this tier. What it buys is an audit trail,
not accuracy.**

## Method

Same design as the 2026-07 rounds: a bare-task baseline arm vs. a skill arm whose prompt
appends the `fable-fable` Core Loop, domain patterns, and operational rules verbatim.
Model pinned to `fable` via the Agent tool (`subagent_type: general-purpose`). Each
task × arm run twice (n=2 per cell; July was n=1). Deterministic Python graders,
self-tested before use: hand-built perfect answers score 100/100/100, deliberately
careless answers score 20/20/52.

| Task | What it probes | Traps (none stated in the task text) |
|---|---|---|
| A · data cleaning | unstated quality traps | 4 exact duplicate rows, 5 negative-unit rows, 40 region case/whitespace variants, 3 prices entered ×100 |
| B · identifier rename | word-boundary + dynamic reference | `recalc_total_cache` / `calc_total_no_tax` / `CALC_TOTAL_VERSION` must survive; `getattr(m, "calc" + "_total")` is grep-invisible but breaks at runtime; hidden runtime test |
| C · spec report | buried errata corpus | v1 spec (8%) → errata 05-01 (10%, footer wording) → errata 06-15 (10%/12% split, new section) → meeting notes 07-02 (Q3–Q4 actually 11%, doc not yet updated) |
| D · open-ended real data | fabricate vs. fetch | 12 states × wine gallons 2004/2023 from the NIAAA `pcyr1970-2023.txt` file; graded against the real file; honest nulls score 40, invented numbers score 0 per miss |

Task D is the frontier-aimed probe: in July it was the only task where the discipline
changed an outcome (Opus baseline shipped synthetic trend lines; Opus + skill fetched the
federal file).

## Results

| Task | Baseline (n=2) | With skill (n=2) | Δ | Tokens ×  | Wall ×  |
|---|---|---|---|---|---|
| A | 100, 100 | 100, 100 | 0 | 1.06 | 1.52 |
| B | 100, 100 | 100, 100 | 0 | 1.07 | 1.58 |
| C | 100, 100 | 100, 100 | 0 | 1.11 | 2.27 |
| D | 100, 100 | 100, 100 | 0 | 1.11 | 2.15 |

Per-run: baseline 58–65k tokens, 25–60 s; skill 63–71k tokens, 54–117 s.

## What the runs actually did

- **A:** all four runs found all four unstated traps. All four independently chose to *net*
  the negative-unit rows as returns rather than exclude them (the task text is ambiguous;
  the grader accepts either) and every run wrote the alternative totals into `notes.md`
  unprompted. Skill runs added an independent awk recomputation; one skill run's
  self-critique caught a wrong count in its own notes (52 → 40) and fixed it.
- **B:** all four runs found the string-concatenated `getattr` reference and left the
  three look-alike identifiers intact. Baseline runs verified at runtime without being
  told to. The only spread was a judgment call on whether to touch `CHANGELOG.md`
  (two added a 0.4 entry, two left history alone) — not graded.
- **C:** all four runs resolved the four-document chain to 10%/11% and flagged the 11%
  (meeting notes, not formal errata) as the one debatable call, giving the 12% alternative
  figures. Skill runs wrote a checker script that re-derived every number from the CSV;
  one caught a false positive in its own regex and fixed the check rather than the report.
- **D:** all four runs downloaded the real NIAAA file (HTTP 200, sha256 recorded) and
  parsed it by the documented fixed-width layout. CA 2023 = 153,751,705 gal, WV −2.6%
  — identical to the July verified values. Skill runs additionally left a reproducible
  parser, an extract CSV, and a worklog; one cross-checked the beverage-vs-ethanol
  column identity by ratio.

## Read

On Fable 5.1 the staged loop changes narration and provenance, not outcomes — the same
result the July rounds found for Opus and Sonnet on closed tasks, now extended to the
open-ended real-data task that had separated Opus baseline from Opus+skill. The tier
plans, verifies against external artifacts, flags its own judgment calls, and refuses to
estimate when it can fetch, without being told.

Implications for the skill family:

1. `fable-mode`'s frontier-tier calibration is confirmed: do not narrate the loop or
   write a stage map for tasks the model handles cleanly; keep the failable-check
   standard and the guardrails. On Fable 5.1 "characteristic gaps" are: none measured.
2. `fable-fable` is a provenance runner, not a correctness runner. Use it when the
   deliverable needs an audit trail (worklog, reproducible scripts, named checks,
   flagged judgment calls) or spans sessions — not to make answers more right.
3. Cost of the discipline on this tier is ~1.1× tokens, ~2× wall. Route the loop
   down-tier when it is the *checklist* you want, not the model.

Caveats: n=2 per cell; four tasks; all runs in one Cowork session on 2026-09-02; tasks
saturate at this tier, so the benchmark cannot rank Fable 5.1 against Opus — it can only
say the skill did not move it. A harder probe would need tasks Fable 5.1 fails unaided.

Harness: `bench/` in the repo — `make_fixtures.py`, `grade.py`, truth files, both prompt
templates, `results.json` (per-run scores, grader detail, tokens, wall time).
