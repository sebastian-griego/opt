# Optimization Constant Search

Purpose: improve a specific optimization constant by producing candidate constructions and scoring them with a local, reproducible evaluator.

Current target constant: C1b (upper bound; better means smaller max overlap). See STATUS.md for definition and the latest bound.

Short iteration (one command):

```bash
python -m pytest -q && \
  python scripts/verify_best_candidate.py --candidate best_candidate.json --max-score 0.387791883827 && \
  python experiments/c1b/search.py --m 50 --seed 0 --steps 1000 && \
  python experiments/c1b/eval.py --candidate best_candidate.json --impl fft
```

## Validation

CI runs the evaluator test suite with `pytest` on Python 3.11. The search step
is intentionally manual because it can produce long-running candidate archives
and updates to `results.csv`.

The committed best candidate also has an exact rational audit:

```bash
python scripts/verify_best_candidate.py --candidate best_candidate.json --out docs/c1b_best_candidate_certificate.md --max-score 0.387791883827
```

The generated certificate records the candidate hash, exact decimal mass error,
mass tolerance, bounds, maximum overlap, and active shift locations.

Audit the candidate archive and confirm the committed best is still rank 1:

```bash
python scripts/audit_candidate_archive.py --check --out-md docs/c1b_candidate_archive_audit.md
```

Add `--strict-results-csv` when the historical search log must have no stale
candidate-path references.
