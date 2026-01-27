# Optimization Constant Search

Purpose: improve a specific optimization constant by producing candidate constructions and scoring them with a local, reproducible evaluator.

Current target constant: C1b (upper bound; better means smaller max overlap). See STATUS.md for definition and the latest bound.

Short iteration (one command):

```bash
python -m pytest -q && \
  python experiments/c1b/search.py --m 50 --seed 0 --steps 1000 && \
  python experiments/c1b/eval.py --candidate best_candidate.json --impl fft
```
