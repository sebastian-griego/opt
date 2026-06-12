# C1b best-candidate certificate

This report audits the committed `best_candidate.json` using exact rational arithmetic
on the decimal values stored in the file. The search itself is heuristic; this
certificate verifies the candidate evaluation and records the mass-tolerance check.

## Candidate

- path: `best_candidate.json`
- SHA256: `c5d3f0b970858666d03966e5104315978644bf56bf1f69c69506ad97d2a17125`
- representation: `piecewise_constant`
- bins `m`: `50`
- grid spacing `dx`: `1/25` = `0.040000000000000000`
- postprocessing: `None`

## Feasibility checks

- exact mass `sum(f) * dx`: `5000000000001107747/5000000000000000000` = `1.000000000000221549`
- mass error: `1107747/5000000000000000000` = `0.000000000000221549`
- mass tolerance: `0.000000001000000000`
- mass within tolerance: `True`
- minimum bin value: `0.056423937554900445`
- maximum bin value: `1.000000000000000000`

## Exact score

- exact max overlap: `19389594191293838178102332539011743/50000000000000000000000000000000000`
- decimal max overlap: `0.387791883825876764`
- evaluated shifts: `101`

## Active shifts

- index `40`, x = `-2/5`, overlap = `0.387791883825876764`

## Threshold check

- claimed maximum: `0.387791883827000000`
- exact score <= claimed maximum: `PASS`

## Reproduce

```bash
python scripts/verify_best_candidate.py --candidate best_candidate.json --out docs/c1b_best_candidate_certificate.md --max-score 0.387791883827
```
