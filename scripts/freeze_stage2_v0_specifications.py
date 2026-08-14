#!/usr/bin/env python3
"""Materialize the frozen D37 40-specification matrix and review packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from safety_stl.stage2_specifications import build_review_records, build_specifications


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=False)
        handle.write("\n")


def _read_if_present(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _reviewable_content(specification: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in specification.items()
        if key not in {
            "independent_reviewer",
            "review_status",
            "source_or_generation_record",
        }
    }


def _preserve_unchanged_reviews(
    specifications: Sequence[Dict[str, Any]],
    reviews: Sequence[Dict[str, Any]],
    existing_specifications: Any,
    existing_reviews: Any,
) -> int:
    if not isinstance(existing_specifications, list) or not isinstance(existing_reviews, list):
        return 0
    old_specs = {str(row.get("spec_id")): row for row in existing_specifications}
    old_reviews = {str(row.get("spec_id")): row for row in existing_reviews}
    review_by_id = {str(row["spec_id"]): row for row in reviews}
    preserved = 0
    for specification in specifications:
        spec_id = str(specification["spec_id"])
        old_spec = old_specs.get(spec_id)
        old_review = old_reviews.get(spec_id)
        if old_spec is None or old_review is None or old_review.get("status") != "approved":
            continue
        if _reviewable_content(old_spec) != _reviewable_content(specification):
            continue
        if not old_review.get("reviewer") or not all(old_review.get("checks", {}).values()):
            continue
        specification["independent_reviewer"] = old_review["reviewer"]
        specification["review_status"] = "independently_reviewed"
        review_by_id[spec_id].update(old_review)
        preserved += 1
    return preserved


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("benchmarks/stage2_v0"),
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    existing_specifications = _read_if_present(args.output_root / "specifications.json")
    existing_reviews = _read_if_present(args.output_root / "reviews.json")
    specifications = build_specifications()
    reviews = build_review_records(specifications)
    preserved_review_count = _preserve_unchanged_reviews(
        specifications,
        reviews,
        existing_specifications,
        existing_reviews,
    )
    _write(args.output_root / "specifications.json", specifications)
    _write(args.output_root / "reviews.json", reviews)
    print(
        json.dumps(
            {
                "specification_count": len(specifications),
                "approved_review_count": sum(row["status"] == "approved" for row in reviews),
                "pending_review_count": sum(row["status"] == "pending" for row in reviews),
                "preserved_unchanged_review_count": preserved_review_count,
            },
            sort_keys=True,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
