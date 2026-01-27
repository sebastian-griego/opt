# Optimization Constant Search

Purpose: improve a specific optimization constant by producing candidate constructions and scoring them with a local, reproducible evaluator.

Current target constant: C1b (see STATUS.md for the latest bound and reproduction details).

Short iteration (one command):

```bash
python -m pytest -q && \
  python experiments/<target>/search.py --m ... --seed ... --steps ... && \
  python experiments/<target>/eval.py --candidate best_candidate.json --m ...
```
