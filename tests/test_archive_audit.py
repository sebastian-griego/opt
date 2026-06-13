from __future__ import annotations

import csv
import json
from fractions import Fraction

from scripts.audit_candidate_archive import (
    audit_candidate_archive,
    audit_results_csv,
    inspect_candidate,
    render_markdown,
)


def _candidate(values: list[float]) -> dict:
    return {
        "representation": "piecewise_constant",
        "m": len(values),
        "f": values,
        "postprocessing": None,
    }


def test_inspect_candidate_reports_exact_score_and_active_shift(tmp_path):
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(_candidate([0.5, 0.5])), encoding="utf-8")

    inspected = inspect_candidate(path, repo_root=tmp_path)

    assert inspected["path"] == "candidate.json"
    assert Fraction(inspected["score"]["fraction"]) == Fraction(1, 2)
    assert inspected["score"]["decimal"] == "0.500000000000000000"
    assert inspected["active_shifts"] == ["0"]


def test_audit_candidate_archive_ranks_best_and_deduplicates(tmp_path):
    candidate_dir = tmp_path / "candidates"
    candidate_dir.mkdir()
    best = candidate_dir / "best.json"
    duplicate = candidate_dir / "duplicate_best.json"
    worse = candidate_dir / "worse.json"
    best.write_text(json.dumps(_candidate([0.5, 0.5])), encoding="utf-8")
    duplicate.write_text(json.dumps(_candidate([0.5, 0.5])), encoding="utf-8")
    worse.write_text(json.dumps(_candidate([0.25, 0.75])), encoding="utf-8")

    audit = audit_candidate_archive(
        tmp_path,
        candidate_dir=candidate_dir,
        best_candidate=best,
        results_csv=None,
    )

    assert audit["candidate_files"] == 3
    assert audit["valid_candidates"] == 3
    assert audit["unique_candidates"] == 2
    assert audit["duplicate_content_count"] == 1
    assert audit["committed_best_rank"] == 1
    assert audit["committed_best_is_archive_best"] is True
    assert audit["top_candidates"][0]["path"] == "candidates/best.json"

    markdown = render_markdown(audit)
    assert "C1b candidate archive audit" in markdown
    assert "candidates/best.json" in markdown


def test_results_csv_cross_check_flags_missing_and_mismatch(tmp_path):
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps(_candidate([0.5, 0.5])), encoding="utf-8")
    inspected = inspect_candidate(candidate, repo_root=tmp_path)
    csv_path = tmp_path / "results.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["candidate_path", "score"])
        writer.writeheader()
        writer.writerow({"candidate_path": "candidate.json", "score": "0.5000000001"})
        writer.writerow({"candidate_path": "missing.json", "score": "0.1"})

    result = audit_results_csv(
        tmp_path,
        csv_path,
        scores_by_path={"candidate.json": Fraction(inspected["score"]["fraction"])},
        tolerance=Fraction("1e-12"),
        decimal_digits=18,
    )

    assert result["ok"] is False
    assert result["missing_candidate_paths"] == ["missing.json"]
    assert len(result["score_mismatches"]) == 1
