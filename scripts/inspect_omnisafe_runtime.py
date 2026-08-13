#!/usr/bin/env python3
"""Write the effective OmniSafe runtime contract for the completed pilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from safety_stl.runtime_contract import DEFAULT_PROTOCOL, inspect_runtime_contract


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/post_pilot_diagnosis/runtime_contract.json"),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    contract = inspect_runtime_contract(args.protocol)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(contract, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"output": str(args.output), "schema_version": 1}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
