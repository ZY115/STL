#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="/home/jerry/anaconda3/envs/stl-stage1/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Missing verified stl-stage1 Python: ${PYTHON_BIN}" >&2
  exit 1
fi

cd "${REPOSITORY_ROOT}"
env PYTHONNOUSERSITE=1 PYTHONPATH=src MUJOCO_GL=egl \
  CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  "${PYTHON_BIN}" scripts/run_stage1_pilot.py "$@"
