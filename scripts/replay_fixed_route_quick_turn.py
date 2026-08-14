#!/usr/bin/env python3
"""Re-evaluate completed D43 final checkpoints and rebuild its figures."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT / "results/fixed_route_v1/quick_turn")
    options = parser.parse_args()
    for phase in ("evaluate", "plot"):
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_fixed_route_quick_turn.py"), "--phase", phase, "--output-root", str(options.output_root)],
            cwd=ROOT,
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
