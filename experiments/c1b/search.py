from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

try:
    from experiments.c1b.eval import DEFAULT_TOL, evaluate, validate_candidate
except ModuleNotFoundError:  # Support running as a script from repo root.
    import sys

    repo_root = Path(__file__).resolve().parents[2]
    sys.path.append(str(repo_root))
    from experiments.c1b.eval import DEFAULT_TOL, evaluate, validate_candidate


def _project_mean_half(values: np.ndarray, tol: float = 1e-12) -> np.ndarray:
    if values.ndim != 1:
        raise ValueError("values must be 1D")
    low, high = -1.0, 1.0
    for _ in range(80):
        mid = 0.5 * (low + high)
        projected = np.clip(values + mid, 0.0, 1.0)
        mean = projected.mean()
        if mean > 0.5:
            high = mid
        else:
            low = mid
        if abs(mean - 0.5) <= tol:
            return projected
    return np.clip(values + 0.5 * (low + high), 0.0, 1.0)


def init_candidate(m: int, rng: np.random.Generator) -> np.ndarray:
    values = rng.random(m)
    return _project_mean_half(values)


def mutate_pair_move(
    f: np.ndarray,
    rng: np.random.Generator,
    delta_fraction: float,
) -> np.ndarray:
    m = f.size
    i, j = rng.integers(0, m, size=2)
    if i == j:
        return f.copy()
    max_delta = min(f[i], 1.0 - f[j])
    if max_delta <= 0.0:
        return f.copy()
    frac = max(0.0, min(1.0, delta_fraction))
    delta = rng.uniform(0.0, 1.0) * frac * max_delta
    if delta <= 0.0:
        return f.copy()
    candidate = f.copy()
    candidate[i] -= delta
    candidate[j] += delta
    return candidate


def mutate_k_swap(
    f: np.ndarray,
    rng: np.random.Generator,
    k: int,
) -> np.ndarray:
    m = f.size
    k = max(2, min(k, m))
    idx = rng.choice(m, size=k, replace=False)
    shuffled = idx.copy()
    while True:
        rng.shuffle(shuffled)
        if not np.array_equal(idx, shuffled):
            break
    candidate = f.copy()
    candidate[idx] = f[shuffled]
    return candidate


def candidate_dict(f: np.ndarray) -> Dict[str, Any]:
    return {
        "representation": "piecewise_constant",
        "m": int(f.size),
        "f": [float(x) for x in f],
        "postprocessing": None,
    }


def write_candidate(path: Path, f: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = candidate_dict(f)
    with path.open("w", encoding="utf-8") as f_out:
        json.dump(data, f_out, indent=2, sort_keys=True)
        f_out.write("\n")


def load_best_candidate(path: Path, eval_impl: str) -> Tuple[Optional[np.ndarray], Optional[float]]:
    if not path.exists():
        return None, None
    try:
        with path.open("r", encoding="utf-8") as f_in:
            data = json.load(f_in)
        f_arr, _m, dx = validate_candidate(data)
        score, _overlaps, _x = evaluate(f_arr, dx, impl=eval_impl)
        return f_arr, score
    except Exception:
        return None, None


def git_commit_hash() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True)
        return out.strip()
    except Exception:
        return "unknown"


def append_results(
    path: Path,
    row: Dict[str, Any],
    header: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8") as f_out:
        if write_header:
            f_out.write(header)
        f_out.write(
            ",".join(str(row.get(col, "")) for col in header.strip().split(",")) + "\n"
        )


def run_search(args: argparse.Namespace) -> int:
    rng = np.random.default_rng(args.seed)
    f = init_candidate(args.m, rng)
    dx = 2.0 / args.m
    current_score, _overlaps, _x = evaluate(f, dx, impl=args.eval_impl)

    accepted = 0
    for _step in range(args.steps):
        if args.operator == "pair":
            candidate = mutate_pair_move(f, rng, args.delta_fraction)
        elif args.operator == "kswap":
            candidate = mutate_k_swap(f, rng, args.kswap_k)
        else:
            raise ValueError("operator must be 'pair' or 'kswap'")

        score, _overlaps, _x = evaluate(candidate, dx, impl=args.eval_impl)
        if score + args.tol < current_score:
            f = candidate
            current_score = score
            accepted += 1
            print(f"accept {accepted} score={current_score:.12f}")
            if args.snapshot_every > 0 and accepted % args.snapshot_every == 0:
                snapshot_path = args.out_dir / (
                    f"candidate_{args.run_id}_acc{accepted}.json"
                )
                write_candidate(snapshot_path, f)

    final_candidate_path = args.candidate_out or args.out_dir / f"candidate_{args.run_id}.json"
    write_candidate(final_candidate_path, f)

    _best_f, best_score = load_best_candidate(args.best_candidate, args.eval_impl)
    improved = best_score is None or current_score + args.tol < best_score
    if improved:
        write_candidate(args.best_candidate, f)
        best_score = current_score

    row = {
        "timestamp": args.timestamp,
        "target": "C1b",
        "direction": "upper",
        "m": args.m,
        "dx": dx,
        "grid_shift": 0,
        "eval_impl": args.eval_impl,
        "search_impl": f"hillclimb_{args.operator}",
        "seed": args.seed,
        "steps": args.steps,
        "score": current_score,
        "best_so_far": best_score,
        "candidate_path": str(final_candidate_path),
        "git_commit": args.git_commit,
    }
    append_results(args.results_path, row, args.results_header)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Baseline hillclimb search for C1b.")
    parser.add_argument("--m", type=int, default=50)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--eval-impl", choices=["slow", "fft"], default="fft")
    parser.add_argument("--operator", choices=["pair", "kswap"], default="pair")
    parser.add_argument("--delta-fraction", type=float, default=0.2)
    parser.add_argument("--kswap-k", type=int, default=3)
    parser.add_argument("--snapshot-every", type=int, default=50)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("experiments/c1b/candidates"),
        help="Directory to write candidate snapshots",
    )
    parser.add_argument(
        "--candidate-out",
        type=Path,
        default=None,
        help="Optional explicit candidate output path",
    )
    parser.add_argument(
        "--best-candidate",
        type=Path,
        default=Path("best_candidate.json"),
    )
    parser.add_argument(
        "--results-path",
        type=Path,
        default=Path("results.csv"),
    )
    parser.add_argument("--tol", type=float, default=DEFAULT_TOL)
    args = parser.parse_args()

    timestamp = datetime.now().isoformat(timespec="seconds")
    run_id = timestamp.replace(":", "").replace("-", "")
    args.timestamp = timestamp
    args.run_id = run_id
    args.git_commit = git_commit_hash()
    args.results_header = (
        "timestamp,target,direction,m,dx,grid_shift,eval_impl,search_impl,"
        "seed,steps,score,best_so_far,candidate_path,git_commit"
    )

    raise SystemExit(run_search(args))


if __name__ == "__main__":
    main()
