from __future__ import annotations

import argparse
import json
from fractions import Fraction
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


def load_candidate_exact(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f, parse_float=Fraction)
    if data.get("representation") != "piecewise_constant":
        raise ValueError("candidate representation must be 'piecewise_constant'")
    return data


def _to_fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, float):
        return Fraction(str(value))
    if isinstance(value, str):
        return Fraction(value)
    raise ValueError("candidate entries must be numeric")


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


def validate_candidate_exact(
    data: Dict[str, Any], tol: float = DEFAULT_TOL
) -> Tuple[list[Fraction], int, Fraction]:
    m = data.get("m")
    if not isinstance(m, int) or m <= 0:
        raise ValueError("candidate must include positive integer 'm'")
    f_vals = data.get("f")
    if not isinstance(f_vals, list) or len(f_vals) != m:
        raise ValueError("candidate 'f' must be a list of length m")
    f_arr = [_to_fraction(v) for v in f_vals]
    tol_frac = Fraction(str(tol)) if tol > 0 else None
    for value in f_arr:
        if tol_frac is None:
            if value < 0 or value > 1:
                raise ValueError("candidate 'f' must be in [0, 1]")
        else:
            if value < -tol_frac or value > 1 + tol_frac:
                raise ValueError("candidate 'f' must be in [0, 1]")
    dx = Fraction(2, m)
    mass = sum(f_arr, Fraction(0)) * dx
    if tol_frac is None:
        if mass != 1:
            raise ValueError(f"mass constraint violated: sum f * dx = {mass}")
    else:
        if abs(float(mass - 1)) > tol:
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


def overlap_curve_exact(f: list[Fraction], dx: Fraction) -> list[Fraction]:
    m = len(f)
    g = [1 - value for value in f]
    overlaps = [Fraction(0) for _ in range(2 * m + 1)]
    for s in range(-(m - 1), m):
        if s >= 0:
            total = sum(f[i] * g[i + s] for i in range(m - s))
        else:
            total = sum(f[i - s] * g[i] for i in range(m + s))
        overlaps[s + m] = total * dx
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


def evaluate_exact(
    f: list[Fraction], dx: Fraction
) -> Tuple[Fraction, list[Fraction], list[Fraction]]:
    overlaps = overlap_curve_exact(f, dx)
    score = max(overlaps)
    x_grid = [Fraction(-2, 1) + dx * i for i in range(len(overlaps))]
    return score, overlaps, x_grid


def evaluate_candidate(path: Path, impl: str = "fft", tol: float = DEFAULT_TOL) -> float:
    if impl == "exact":
        score = evaluate_candidate_exact(path, tol=tol)
        return float(score)
    data = load_candidate(path)
    f_arr, _m, dx = validate_candidate(data, tol=tol)
    score, _overlaps, _x_grid = evaluate(f_arr, dx, impl=impl)
    return score


def evaluate_candidate_exact(path: Path, tol: float = DEFAULT_TOL) -> Fraction:
    data = load_candidate_exact(path)
    f_arr, _m, dx = validate_candidate_exact(data, tol=tol)
    score, _overlaps, _x_grid = evaluate_exact(f_arr, dx)
    return score


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate C1b candidate.")
    parser.add_argument("--candidate", required=True, type=Path, help="Path to candidate JSON")
    parser.add_argument(
        "--impl",
        default="fft",
        choices=["slow", "fft", "exact"],
        help="Evaluation implementation",
    )
    parser.add_argument("--tol", type=float, default=DEFAULT_TOL, help="Validation tolerance")
    args = parser.parse_args()

    score = evaluate_candidate(args.candidate, impl=args.impl, tol=args.tol)
    print(f"{score:.12f}")


if __name__ == "__main__":
    main()
