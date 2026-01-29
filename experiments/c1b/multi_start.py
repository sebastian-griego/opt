from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict


def _read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        return list(reader)


def _run_search(
    search_path: Path,
    seed: int,
    args: argparse.Namespace,
    run_tag: str,
) -> Path:
    candidate_out = Path(args.out_dir) / f"candidate_ms_{run_tag}_seed{seed}.json"
    cmd = [
        sys.executable,
        str(search_path),
        "--m",
        str(args.m),
        "--steps",
        str(args.steps),
        "--seed",
        str(seed),
        "--eval-impl",
        args.eval_impl,
        "--operator",
        args.operator,
        "--delta-fraction",
        str(args.delta_fraction),
        "--kswap-k",
        str(args.kswap_k),
        "--snapshot-every",
        str(args.snapshot_every),
        "--out-dir",
        str(args.out_dir),
        "--candidate-out",
        str(candidate_out),
        "--best-candidate",
        str(args.best_candidate),
        "--results-path",
        str(args.results_path),
        "--tol",
        str(args.tol),
    ]
    subprocess.run(cmd, check=True)
    return candidate_out


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-start wrapper for C1b search.")
    parser.add_argument("--m", type=int, default=50)
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--seed-start", type=int, default=0)
    parser.add_argument("--num-seeds", type=int, default=3)
    parser.add_argument("--eval-impl", choices=["slow", "fft"], default="fft")
    parser.add_argument("--operator", choices=["pair", "kswap"], default="pair")
    parser.add_argument("--delta-fraction", type=float, default=0.2)
    parser.add_argument("--kswap-k", type=int, default=3)
    parser.add_argument("--snapshot-every", type=int, default=0)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("experiments/c1b/candidates"),
        help="Directory to write candidate outputs",
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
    parser.add_argument("--tol", type=float, default=1e-9)
    args = parser.parse_args()

    search_path = Path(__file__).resolve().parent / "search.py"
    start_rows = len(_read_rows(args.results_path))
    run_tag = datetime.now().strftime("%Y%m%dT%H%M%S")

    for offset in range(args.num_seeds):
        seed = args.seed_start + offset
        _run_search(search_path, seed, args, run_tag)

    rows = _read_rows(args.results_path)
    new_rows = rows[start_rows:]
    if not new_rows:
        print("multi-start: no new results appended")
        return

    best_row = min(new_rows, key=lambda row: float(row["score"]))
    print(
        "multi-start: best_score="
        f"{best_row['score']} seed={best_row['seed']} runs={len(new_rows)}"
    )


if __name__ == "__main__":
    main()
