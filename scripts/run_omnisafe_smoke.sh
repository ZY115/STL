#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
runner="${repository_root}/scripts/run_omnisafe_integration_smoke.py"

if [[ "${CONDA_DEFAULT_ENV:-}" == "stl-stage1" && -n "${CONDA_PREFIX:-}" ]]; then
    exec env PYTHONNOUSERSITE=1 PYTHONPATH= MUJOCO_GL=egl \
        "${CONDA_PREFIX}/bin/python" "${runner}" "$@"
fi

if [[ -n "${CONDA_EXE:-}" && -x "${CONDA_EXE}" ]]; then
    exec env PYTHONNOUSERSITE=1 PYTHONPATH= MUJOCO_GL=egl \
        "${CONDA_EXE}" run --no-capture-output -n stl-stage1 python "${runner}" "$@"
fi

if command -v conda >/dev/null 2>&1; then
    exec env PYTHONNOUSERSITE=1 PYTHONPATH= MUJOCO_GL=egl \
        conda run --no-capture-output -n stl-stage1 python "${runner}" "$@"
fi

echo "Could not find Conda. Activate stl-stage1 and run this command again." >&2
exit 2
