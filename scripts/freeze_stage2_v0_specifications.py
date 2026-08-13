#!/usr/bin/env python3
"""Materialize the frozen D37 40-specification matrix and review packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional, Sequence

from safety_stl.stage2_specifications import build_review_records, build_specifications


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=False)
        handle.write("\n")


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
    specifications = build_specifications()
    reviews = build_review_records(specifications)
    _write(args.output_root / "specifications.json", specifications)
    _write(args.output_root / "reviews.json", reviews)
    print(
        json.dumps(
            {
                "specification_count": len(specifications),
                "approved_review_count": sum(row["status"] == "approved" for row in reviews),
                "pending_review_count": sum(row["status"] == "pending" for row in reviews),
            },
            sort_keys=True,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
