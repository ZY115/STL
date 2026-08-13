#!/usr/bin/env python3
"""Export the frozen Stage II v0 records as a human-review Markdown packet."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

from safety_stl.stage2_review import render_review_packet


DEFAULT_ROOT = Path("benchmarks/stage2_v0")
def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = args.benchmark_root.resolve()
    output = (
        args.output.resolve()
        if args.output is not None
        else root / "independent_review_packet.md"
    )
    rendered = render_review_packet(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
