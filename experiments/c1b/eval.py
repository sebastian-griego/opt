from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np


DEFAULT_TOL = 1e-9


def load_candidate(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("representation") != "piecewise_constant":
        raise ValueError("candidate representation must be 'piecewise_constant'")
    return data


def validate_candidate(data: Dict[str, Any], tol: float = DEFAULT_TOL) -> Tuple[np.ndarray, int, float]:
    m = data.get("m")
    if not isinstance(m, int) or m <= 0:
        raise ValueError("candidate must include positive integer 'm'")
    f_vals = data.get("f")
    if not isinstance(f_vals, list) or len(f_vals) != m:
        raise ValueError("candidate 'f' must be a list of length m")
    f_arr = np.asarray(f_vals, dtype=float)
    if np.any(f_arr < -tol) or np.any(f_arr > 1.0 + tol):
        raise ValueError("candidate 'f' must be in [0, 1]")
    f_arr = np.clip(f_arr, 0.0, 1.0)
    dx = 2.0 / m
    mass = float(f_arr.sum() * dx)
    if abs(mass - 1.0) > tol:
        raise ValueError(f"mass constraint violated: sum f * dx = {mass}")
    return f_arr, m, dx


def overlap_curve_slow(f: np.ndarray, dx: float) -> np.ndarray:
    m = f.size
    g = 1.0 - f
    overlaps = np.zeros(2 * m + 1, dtype=float)
    for s in range(-(m - 1), m):
        if s >= 0:
            overlaps[s + m] = float(np.dot(f[: m - s], g[s:])) * dx
        else:
            overlaps[s + m] = float(np.dot(f[-s:], g[: m + s])) * dx
    return overlaps


def overlap_curve_fft(f: np.ndarray, dx: float) -> np.ndarray:
    m = f.size
    g_rev = (1.0 - f)[::-1]
    n = 1 << (2 * m - 1).bit_length()
    F = np.fft.rfft(f, n)
    G = np.fft.rfft(g_rev, n)
    conv = np.fft.irfft(F * G, n)[: 2 * m - 1]
    conv = conv * dx
    overlaps = np.zeros(2 * m + 1, dtype=float)
    overlaps[1:-1] = conv[::-1]
    return overlaps


def evaluate(f: np.ndarray, dx: float, impl: str = "fft") -> Tuple[float, np.ndarray, np.ndarray]:
    if impl == "slow":
        overlaps = overlap_curve_slow(f, dx)
    elif impl == "fft":
        overlaps = overlap_curve_fft(f, dx)
    else:
        raise ValueError("impl must be 'slow' or 'fft'")
    x_grid = np.linspace(-2.0, 2.0, overlaps.size)
    score = float(overlaps.max())
    return score, overlaps, x_grid


def evaluate_candidate(path: Path, impl: str = "fft", tol: float = DEFAULT_TOL) -> float:
    data = load_candidate(path)
    f_arr, _m, dx = validate_candidate(data, tol=tol)
    score, _overlaps, _x_grid = evaluate(f_arr, dx, impl=impl)
    return score


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate C1b candidate.")
    parser.add_argument("--candidate", required=True, type=Path, help="Path to candidate JSON")
    parser.add_argument("--impl", default="fft", choices=["slow", "fft"], help="Evaluation implementation")
    parser.add_argument("--tol", type=float, default=DEFAULT_TOL, help="Validation tolerance")
    args = parser.parse_args()

    score = evaluate_candidate(args.candidate, impl=args.impl, tol=args.tol)
    print(f"{score:.12f}")


if __name__ == "__main__":
    main()
