from __future__ import annotations

import json
from fractions import Fraction

from experiments.c1b.certificate import build_certificate, markdown_report


def test_build_certificate_for_constant_half_candidate(tmp_path):
    candidate = {
        "representation": "piecewise_constant",
        "m": 4,
        "f": [0.5, 0.5, 0.5, 0.5],
        "postprocessing": None,
    }
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(candidate), encoding="utf-8")

    cert = build_certificate(path)

    assert cert["m"] == 4
    assert Fraction(cert["mass"]["fraction"]) == 1
    assert Fraction(cert["mass_error"]["fraction"]) == 0
    assert cert["mass_within_tolerance"] is True
    assert Fraction(cert["score"]["fraction"]) == Fraction(1, 2)
    assert cert["active_shifts"] == [
        {
            "index": 4,
            "shift": "0",
            "overlap": {
                "fraction": "1/2",
                "decimal": "0.500000000000000000",
            },
        }
    ]
    assert cert["candidate_sha256"]


def test_markdown_report_includes_threshold_status(tmp_path):
    candidate = {
        "representation": "piecewise_constant",
        "m": 2,
        "f": [0.5, 0.5],
        "postprocessing": None,
    }
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(candidate), encoding="utf-8")

    cert = build_certificate(path)
    report = markdown_report(cert, max_score=Fraction(1, 2))

    assert "C1b best-candidate certificate" in report
    assert "exact score <= claimed maximum: `PASS`" in report
