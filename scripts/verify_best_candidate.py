#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.c1b.certificate import build_certificate, fraction_decimal, markdown_report


def parse_fraction_or_decimal(text: str) -> Fraction:
    return Fraction(text)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the committed C1b best candidate with exact arithmetic."
    )
    parser.add_argument("--candidate", type=Path, default=ROOT / "best_candidate.json")
    parser.add_argument("--out", type=Path, default=None, help="Optional markdown report path")
    parser.add_argument(
        "--max-score",
        type=parse_fraction_or_decimal,
        default=None,
        help="Optional exact/decimal threshold. The command fails if score is larger.",
    )
    parser.add_argument("--decimal-digits", type=int, default=18)
    parser.add_argument(
        "--mass-tol",
        type=parse_fraction_or_decimal,
        default=Fraction("1e-9"),
        help="Allowed absolute mass error for decimal candidates.",
    )
    args = parser.parse_args()

    certificate = build_certificate(
        args.candidate,
        decimal_digits=args.decimal_digits,
        mass_tolerance=args.mass_tol,
    )
    score = Fraction(certificate["score"]["fraction"])
    print(f"candidate: {args.candidate}")
    print(f"sha256: {certificate['candidate_sha256']}")
    print(f"exact score: {score}")
    print(f"decimal score: {certificate['score']['decimal']}")
    print(f"mass error: {certificate['mass_error']['decimal']}")
    print(f"mass tolerance: {certificate['mass_tolerance']['decimal']}")
    print("active shifts:")
    for item in certificate["active_shifts"]:
        print(f"  index={item['index']} x={item['shift']} overlap={item['overlap']['decimal']}")

    if args.max_score is not None:
        print(f"threshold: {fraction_decimal(args.max_score, digits=args.decimal_digits)}")
        if score > args.max_score:
            print(
                "FAIL: exact score exceeds threshold "
                f"({certificate['score']['decimal']} > {fraction_decimal(args.max_score, digits=args.decimal_digits)})",
                file=sys.stderr,
            )
            return 1
        print("PASS: exact score is within threshold")

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            markdown_report(certificate, max_score=args.max_score),
            encoding="utf-8",
            newline="\n",
        )
        print(f"wrote {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
