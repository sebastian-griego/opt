#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.c1b.certificate import fraction_decimal, sha256_file
from experiments.c1b.eval import (
    load_candidate_exact,
    validate_candidate_exact,
    evaluate_exact,
)


def audit_candidate_archive(
    repo_root: Path,
    *,
    candidate_dir: Path,
    best_candidate: Path,
    results_csv: Path | None = None,
    top_n: int = 10,
    decimal_digits: int = 18,
    csv_tolerance: Fraction = Fraction("1e-9"),
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    candidate_dir = _resolve(repo_root, candidate_dir)
    best_candidate = _resolve(repo_root, best_candidate)
    if results_csv is not None:
        results_csv = _resolve(repo_root, results_csv)

    candidate_paths = sorted(candidate_dir.glob("*.json"))
    inspected: list[dict[str, Any]] = []
    invalid: list[dict[str, str]] = []
    by_sha: dict[str, list[Path]] = defaultdict(list)

    for path in candidate_paths:
        try:
            sha = sha256_file(path)
            by_sha[sha].append(path)
            inspected.append(
                inspect_candidate(
                    path,
                    repo_root=repo_root,
                    sha256=sha,
                    decimal_digits=decimal_digits,
                )
            )
        except Exception as exc:  # noqa: BLE001
            invalid.append({"path": _rel(repo_root, path), "error": str(exc)})

    unique_by_sha: dict[str, dict[str, Any]] = {}
    for item in inspected:
        sha = item["sha256"]
        current = unique_by_sha.get(sha)
        if current is None or item["path"] < current["path"]:
            unique_by_sha[sha] = item

    ranked = sorted(
        unique_by_sha.values(),
        key=lambda item: (Fraction(item["score"]["fraction"]), item["path"]),
    )
    best_sha = sha256_file(best_candidate) if best_candidate.exists() else ""
    committed_rank = None
    for idx, item in enumerate(ranked, 1):
        if item["sha256"] == best_sha:
            committed_rank = idx
            break

    csv_check = (
        audit_results_csv(
            repo_root,
            results_csv,
            scores_by_path={
                item["path"]: Fraction(item["score"]["fraction"]) for item in inspected
            },
            tolerance=csv_tolerance,
            decimal_digits=decimal_digits,
        )
        if results_csv is not None and results_csv.exists()
        else None
    )

    duplicate_groups = [
        {
            "sha256": sha,
            "count": len(paths),
            "paths": [_rel(repo_root, path) for path in sorted(paths)],
        }
        for sha, paths in sorted(by_sha.items())
        if len(paths) > 1
    ]

    top = ranked[: max(0, top_n)]
    return {
        "candidate_dir": _rel(repo_root, candidate_dir),
        "candidate_files": len(candidate_paths),
        "valid_candidates": len(inspected),
        "invalid_candidates": invalid,
        "unique_candidates": len(ranked),
        "duplicate_content_groups": duplicate_groups,
        "duplicate_content_count": sum(
            group["count"] - 1 for group in duplicate_groups
        ),
        "best_candidate": _rel(repo_root, best_candidate),
        "best_candidate_sha256": best_sha,
        "committed_best_rank": committed_rank,
        "committed_best_is_archive_best": committed_rank == 1,
        "archive_best": top[0] if top else None,
        "top_candidates": top,
        "results_csv_check": csv_check,
    }


def inspect_candidate(
    path: Path,
    *,
    repo_root: Path,
    sha256: str | None = None,
    decimal_digits: int = 18,
) -> dict[str, Any]:
    data = load_candidate_exact(path)
    f_values, m, dx = validate_candidate_exact(data)
    score, overlaps, x_grid = evaluate_exact(f_values, dx)
    mass = sum(f_values, Fraction(0)) * dx
    active_indices = [idx for idx, value in enumerate(overlaps) if value == score]
    return {
        "path": _rel(repo_root, path),
        "sha256": sha256 or sha256_file(path),
        "m": m,
        "dx": str(dx),
        "mass_error": {
            "fraction": str(mass - 1),
            "decimal": fraction_decimal(mass - 1, digits=decimal_digits),
        },
        "score": {
            "fraction": str(score),
            "decimal": fraction_decimal(score, digits=decimal_digits),
        },
        "active_shift_count": len(active_indices),
        "active_shifts": [str(x_grid[idx]) for idx in active_indices],
    }


def audit_results_csv(
    repo_root: Path,
    results_csv: Path,
    *,
    scores_by_path: dict[str, Fraction],
    tolerance: Fraction,
    decimal_digits: int,
) -> dict[str, Any]:
    rows = []
    with results_csv.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)

    matched = 0
    missing: list[str] = []
    mismatches: list[dict[str, Any]] = []
    for row in rows:
        candidate_path = str(row.get("candidate_path", "")).strip()
        if not candidate_path:
            continue
        exact_score = scores_by_path.get(candidate_path)
        if exact_score is None:
            missing.append(candidate_path)
            continue
        matched += 1
        logged_score = Fraction(str(row.get("score", "0")))
        delta = abs(exact_score - logged_score)
        if delta > tolerance:
            mismatches.append(
                {
                    "candidate_path": candidate_path,
                    "logged_score": str(logged_score),
                    "exact_score": str(exact_score),
                    "delta": fraction_decimal(delta, digits=decimal_digits),
                }
            )

    return {
        "path": _rel(repo_root, results_csv),
        "rows": len(rows),
        "matched_candidate_rows": matched,
        "missing_candidate_paths": sorted(set(missing)),
        "score_tolerance": str(tolerance),
        "score_mismatches": mismatches,
        "ok": not missing and not mismatches,
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# C1b candidate archive audit",
        "",
        f"- candidate files: `{audit['candidate_files']}`",
        f"- valid candidates: `{audit['valid_candidates']}`",
        f"- unique candidates: `{audit['unique_candidates']}`",
        f"- duplicate content files: `{audit['duplicate_content_count']}`",
        f"- committed best rank: `{audit['committed_best_rank']}`",
        f"- committed best is archive best: `{audit['committed_best_is_archive_best']}`",
        "",
        "## Top candidates",
        "",
        "| Rank | Path | Exact score | Active shifts | SHA256 |",
        "|---:|---|---:|---:|---|",
    ]
    for idx, item in enumerate(audit["top_candidates"], 1):
        lines.append(
            f"| {idx} | `{item['path']}` | `{item['score']['decimal']}` | "
            f"{item['active_shift_count']} | `{item['sha256']}` |"
        )

    csv_check = audit.get("results_csv_check")
    if csv_check is not None:
        lines.extend(
            [
                "",
                "## results.csv cross-check",
                "",
                f"- rows: `{csv_check['rows']}`",
                f"- matched candidate rows: `{csv_check['matched_candidate_rows']}`",
                f"- missing candidate paths: `{len(csv_check['missing_candidate_paths'])}`",
                f"- score mismatches: `{len(csv_check['score_mismatches'])}`",
                f"- ok: `{csv_check['ok']}`",
            ]
        )

    if audit["invalid_candidates"]:
        lines.extend(["", "## Invalid candidates", ""])
        for item in audit["invalid_candidates"]:
            lines.append(f"- `{item['path']}`: {item['error']}")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit and rank archived C1b candidates."
    )
    parser.add_argument(
        "--candidate-dir", type=Path, default=ROOT / "experiments/c1b/candidates"
    )
    parser.add_argument(
        "--best-candidate", type=Path, default=ROOT / "best_candidate.json"
    )
    parser.add_argument("--results-csv", type=Path, default=ROOT / "results.csv")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--strict-results-csv",
        action="store_true",
        help="Make --check fail if results.csv has missing paths or score mismatches.",
    )
    args = parser.parse_args()

    audit = audit_candidate_archive(
        ROOT,
        candidate_dir=args.candidate_dir,
        best_candidate=args.best_candidate,
        results_csv=args.results_csv,
        top_n=args.top_n,
    )
    print(
        json.dumps(
            {
                "candidate_files": audit["candidate_files"],
                "unique_candidates": audit["unique_candidates"],
                "committed_best_rank": audit["committed_best_rank"],
                "committed_best_is_archive_best": audit[
                    "committed_best_is_archive_best"
                ],
                "invalid_candidates": len(audit["invalid_candidates"]),
                "results_csv_ok": (
                    None
                    if audit["results_csv_check"] is None
                    else audit["results_csv_check"]["ok"]
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )

    if args.out_json is not None:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(
            json.dumps(audit, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.out_md is not None:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(render_markdown(audit), encoding="utf-8")

    if args.check:
        csv_ok = (
            True
            if audit["results_csv_check"] is None
            else audit["results_csv_check"]["ok"]
        )
        if (
            audit["invalid_candidates"]
            or audit["committed_best_rank"] != 1
            or (args.strict_results_csv and not csv_ok)
        ):
            return 1
    return 0


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _rel(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
