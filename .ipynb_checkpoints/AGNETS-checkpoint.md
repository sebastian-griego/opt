# Project goal
Improve a specific optimization constant by producing candidates and measuring them with a local, reproducible evaluator.

# Hard requirements
- All progress must be measurable by running the evaluator.
- Never change the definition of the objective without adding tests that would fail on the old definition.
- Prefer small diffs. Avoid refactors unless they unblock speed, correctness, or search quality.
- No network access is assumed. Do not attempt installs that require network.

# Files that are the source of truth
- STATUS.md: current best number, where it came from, how to reproduce it
- TODO.md: prioritized, bite-sized next steps
- results.csv: append-only run log
- best_candidate.*: current best construction/certificate

# One-iteration loop (this is what "continue" means)
On each "continue":
1) Read STATUS.md and TODO.md.
2) Select the highest priority TODO that can be completed end-to-end.
3) Implement it.
4) Run: python -m pytest -q  (or the repo's test command)
5) Run the evaluator and at least one short search run.
6) Append a row to results.csv with params, score, seed, git commit hash.
7) Update STATUS.md with:
   - best score so far
   - exact command lines to reproduce
   - what changed in this iteration
   - the next TODO item
8) Commit with a message: "iter: <short description>".
Stop after one iteration.
