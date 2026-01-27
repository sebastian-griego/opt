import numpy as np
import pytest

from experiments.c1b.eval import (
    DEFAULT_TOL,
    evaluate,
    overlap_curve_fft,
    overlap_curve_slow,
    validate_candidate,
)


def _candidate_dict(f):
    return {
        "representation": "piecewise_constant",
        "m": len(f),
        "f": list(map(float, f)),
        "postprocessing": None,
    }


def _make_random_feasible(m, rng):
    f = rng.uniform(0.1, 0.9, size=m)
    f += 0.5 - f.mean()
    if f.min() < 0.0 or f.max() > 1.0:
        noise = rng.uniform(-0.05, 0.05, size=m)
        noise -= noise.mean()
        f = 0.5 + noise
    assert f.min() >= 0.0
    assert f.max() <= 1.0
    return f


def test_constant_half_tent():
    m = 20
    f = np.full(m, 0.5)
    data = _candidate_dict(f)
    f_arr, _m, dx = validate_candidate(data)
    overlaps = overlap_curve_slow(f_arr, dx)

    expected = np.array([0.5 * (1.0 - abs(k) / m) for k in range(-m, m + 1)])
    assert overlaps[m] == pytest.approx(0.5, abs=1e-12)
    assert overlaps[0] == pytest.approx(0.0, abs=1e-12)
    assert overlaps[-1] == pytest.approx(0.0, abs=1e-12)
    assert np.allclose(overlaps, expected, atol=1e-12)
    assert np.allclose(overlaps, overlaps[::-1], atol=1e-12)


def test_bounds_validation():
    f = [0.5, -0.1]
    data = _candidate_dict(f)
    data["m"] = 2
    with pytest.raises(ValueError):
        validate_candidate(data)


def test_mass_constraint_validation():
    m = 10
    f = np.full(m, 0.6)
    data = _candidate_dict(f)
    with pytest.raises(ValueError):
        validate_candidate(data)


def test_symmetric_candidate_overlap_is_symmetric():
    m = 20
    rng = np.random.default_rng(0)
    half = rng.uniform(-0.05, 0.05, size=m // 2)
    half -= half.mean()
    f_half = 0.5 + half
    f = np.concatenate([f_half, f_half[::-1]])
    data = _candidate_dict(f)
    f_arr, _m, dx = validate_candidate(data)
    overlaps = overlap_curve_slow(f_arr, dx)
    assert np.allclose(overlaps, overlaps[::-1], atol=1e-12)


def test_fft_matches_slow():
    rng = np.random.default_rng(1)
    for m in (30, 40, 50):
        for _ in range(3):
            f = _make_random_feasible(m, rng)
            data = _candidate_dict(f)
            f_arr, _m, dx = validate_candidate(data, tol=DEFAULT_TOL)
            slow = overlap_curve_slow(f_arr, dx)
            fast = overlap_curve_fft(f_arr, dx)
            assert np.allclose(slow, fast, atol=1e-10)
            slow_score, _, _ = evaluate(f_arr, dx, impl="slow")
            fast_score, _, _ = evaluate(f_arr, dx, impl="fft")
            assert slow_score == pytest.approx(fast_score, abs=1e-10)
