# Current target
Constant: C1b
Direction: upper bound (smaller is better)

Definition (C1b):
- Choose f, g: [-1, 1] -> [0, 1] with f + g = 1 on [-1, 1] and integral_{-1}^1 f = 1.
- Extend f and g by 0 outside [-1, 1].
- Overlap curve: x in [-2, 2] |-> integral_{-1}^1 f(t) * g(x + t) dt.
- C1b is the largest constant guaranteed to be <= sup_x integral f(t) g(x + t) dt for all feasible (f, g).

Search objective (upper bound):
- Construct f (with g = 1 - f on [-1, 1]) to minimize max_{x in [-2, 2]} integral_{-1}^1 f(t) * (1 - f(x + t)) dt.

Global best known bounds (reference):
- 0.379005 <= C1b <= 0.380876 (from optimizationproblems table; see user-provided reference, captured 2026-01-27)

# Best known (local)
Best value: 0.436281379256 (m=50, fft eval)
Found by: hillclimb_kswap (steps=200, seed=4)
Reproduce: python experiments/c1b/search.py --m 50 --seed 4 --steps 200 --operator kswap --snapshot-every 0
Verify: python experiments/c1b/eval.py --candidate best_candidate.json --impl fft

# Evaluator definition snapshot
Grid: x in [-2, 2] with 2m + 1 points, step dx = 2/m
Shift grid: integer shifts s in [-m, m], x = s * dx
Any smoothing: none (piecewise-constant bins)

# Last iteration summary
- Change: Ran m=60 and m=80 short kswap runs (steps=200) and logged both.
- Result: m=60 best 0.437000484960; m=80 best 0.470842882876; overall best remains 0.436281379256.
- Next: Expand kswap runs at m=50 with multiple seeds (same steps) to see if best improves.
