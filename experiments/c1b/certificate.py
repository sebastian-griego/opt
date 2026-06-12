from __future__ import annotations

import hashlib
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any

from experiments.c1b.eval import DEFAULT_TOL, evaluate_exact, load_candidate_exact, validate_candidate_exact


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fraction_decimal(value: Fraction, digits: int = 18) -> str:
    with localcontext() as ctx:
        ctx.prec = digits + 20
        decimal = Decimal(value.numerator) / Decimal(value.denominator)
        return f"{decimal:.{digits}f}"


def _fraction_payload(value: Fraction, digits: int = 18) -> dict[str, str]:
    return {
        "fraction": f"{value.numerator}/{value.denominator}",
        "decimal": fraction_decimal(value, digits=digits),
    }


def build_certificate(
    candidate_path: Path,
    decimal_digits: int = 18,
    mass_tolerance: Fraction = Fraction(str(DEFAULT_TOL)),
) -> dict[str, Any]:
    data = load_candidate_exact(candidate_path)
    f_values, m, dx = validate_candidate_exact(data, tol=float(mass_tolerance))
    score, overlaps, x_grid = evaluate_exact(f_values, dx)
    active = [
        {
            "index": idx,
            "shift": str(x_grid[idx]),
            "overlap": _fraction_payload(value, digits=decimal_digits),
        }
        for idx, value in enumerate(overlaps)
        if value == score
    ]

    mass = sum(f_values, Fraction(0)) * dx
    mass_error = mass - 1
    return {
        "candidate_path": str(candidate_path),
        "candidate_sha256": sha256_file(candidate_path),
        "representation": data["representation"],
        "m": m,
        "dx": _fraction_payload(dx, digits=decimal_digits),
        "mass": _fraction_payload(mass, digits=decimal_digits),
        "mass_error": _fraction_payload(mass_error, digits=decimal_digits),
        "mass_tolerance": _fraction_payload(mass_tolerance, digits=decimal_digits),
        "mass_within_tolerance": abs(mass_error) <= mass_tolerance,
        "min_f": _fraction_payload(min(f_values), digits=decimal_digits),
        "max_f": _fraction_payload(max(f_values), digits=decimal_digits),
        "score": _fraction_payload(score, digits=decimal_digits),
        "active_shifts": active,
        "num_shifts": len(overlaps),
        "postprocessing": data.get("postprocessing"),
    }


def markdown_report(certificate: dict[str, Any], max_score: Fraction | None = None) -> str:
    active_lines = []
    for item in certificate["active_shifts"]:
        active_lines.append(
            f"- index `{item['index']}`, x = `{item['shift']}`, "
            f"overlap = `{item['overlap']['decimal']}`"
        )
    if not active_lines:
        active_lines.append("- none")

    threshold_lines = []
    if max_score is not None:
        score = Fraction(certificate["score"]["fraction"])
        status = "PASS" if score <= max_score else "FAIL"
        threshold_lines.extend(
            [
                "## Threshold check",
                "",
                f"- claimed maximum: `{fraction_decimal(max_score, digits=18)}`",
                f"- exact score <= claimed maximum: `{status}`",
                "",
            ]
        )

    lines = [
        "# C1b best-candidate certificate",
        "",
        "This report audits the committed `best_candidate.json` using exact rational arithmetic",
        "on the decimal values stored in the file. The search itself is heuristic; this",
        "certificate verifies the candidate evaluation and records the mass-tolerance check.",
        "",
        "## Candidate",
        "",
        f"- path: `{certificate['candidate_path']}`",
        f"- SHA256: `{certificate['candidate_sha256']}`",
        f"- representation: `{certificate['representation']}`",
        f"- bins `m`: `{certificate['m']}`",
        f"- grid spacing `dx`: `{certificate['dx']['fraction']}` = `{certificate['dx']['decimal']}`",
        f"- postprocessing: `{certificate['postprocessing']}`",
        "",
        "## Feasibility checks",
        "",
        f"- exact mass `sum(f) * dx`: `{certificate['mass']['fraction']}` = `{certificate['mass']['decimal']}`",
        f"- mass error: `{certificate['mass_error']['fraction']}` = `{certificate['mass_error']['decimal']}`",
        f"- mass tolerance: `{certificate['mass_tolerance']['decimal']}`",
        f"- mass within tolerance: `{certificate['mass_within_tolerance']}`",
        f"- minimum bin value: `{certificate['min_f']['decimal']}`",
        f"- maximum bin value: `{certificate['max_f']['decimal']}`",
        "",
        "## Exact score",
        "",
        f"- exact max overlap: `{certificate['score']['fraction']}`",
        f"- decimal max overlap: `{certificate['score']['decimal']}`",
        f"- evaluated shifts: `{certificate['num_shifts']}`",
        "",
        "## Active shifts",
        "",
        *active_lines,
        "",
        *threshold_lines,
        "## Reproduce",
        "",
        "```bash",
        "python scripts/verify_best_candidate.py --candidate best_candidate.json --out docs/c1b_best_candidate_certificate.md --max-score 0.387791883827",
        "```",
        "",
    ]
    return "\n".join(lines)
