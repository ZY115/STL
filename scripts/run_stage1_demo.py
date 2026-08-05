#!/usr/bin/env python3
"""Start the Stage I simulator/monitor visualization."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def requested_render(argv: list) -> str:
    """Read --render early so MuJoCo sees the correct backend at import time."""

    for index, value in enumerate(argv):
        if value.startswith("--render="):
            return value.split("=", maxsplit=1)[1]
        if value == "--render" and index + 1 < len(argv):
            return argv[index + 1]
    return "human"


render_mode = requested_render(sys.argv[1:])
os.environ["MUJOCO_GL"] = "glfw" if render_mode == "human" else "egl"

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from safety_stl.visualization import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
