# Benchmark harness (2026-09-02)

- `make_fixtures.py` — builds `fixtures/task{A,B,C}` deterministically and writes `truthA.json`, `truthC.json`. Task D's fixture is a single `TASK.md` (see `BENCHMARK-2026-09-02.md`); `truthD.json` was derived from the real NIAAA `pcyr1970-2023.txt`.
- `grade.py <A|B|C|D> <run_dir>` — deterministic grader, prints `{score, detail}`. Self-test: perfect answers → 100, careless → 20/20/52.
- `prompt_base.txt` / `prompt_skill.txt` — the two arms (`{d}` = run dir). The skill arm appends `skill_briefing.md`, which is the `fable-fable` Core Loop + domain patterns + operational rules verbatim.
- `results.json` — 16 runs: score, grader detail, subagent tokens, wall ms.

Run: `python make_fixtures.py`, copy a fixture to `runs/<task>_<arm>_<n>`, spawn an agent with the prompt (model `fable`), then `python grade.py <task> runs/<dir>`.
