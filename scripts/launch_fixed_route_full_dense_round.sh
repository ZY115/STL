#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output_root="${repo_root}/results/fixed_route_v1/full_dense_round"
python_bin="/home/jerry/anaconda3/envs/stl-stage1/bin/python"

mkdir -p "${output_root}"
cd "${repo_root}"

export PYTHONNOUSERSITE=1
export PYTHONUNBUFFERED=1
export PYTHONPATH="${repo_root}/src"
export MUJOCO_GL=egl
export CUBLAS_WORKSPACE_CONFIG=:4096:8

service_unit="stl-fixed-route-full-dense.service"
launcher_log="${output_root}/launcher.log"

if systemctl --user is-active --quiet "${service_unit}"; then
  printf 'service already active: %s\n' "${service_unit}" >&2
  exit 1
fi
systemctl --user reset-failed "${service_unit}" 2>/dev/null || true
systemd-run --user \
  --unit="${service_unit}" \
  --description="STL fixed-route full C1-dense round" \
  --property="WorkingDirectory=${repo_root}" \
  --property="StandardOutput=append:${launcher_log}" \
  --property="StandardError=append:${launcher_log}" \
  --setenv=PYTHONNOUSERSITE=1 \
  --setenv=PYTHONUNBUFFERED=1 \
  --setenv="PYTHONPATH=${repo_root}/src" \
  --setenv=MUJOCO_GL=egl \
  --setenv=CUBLAS_WORKSPACE_CONFIG=:4096:8 \
  "${python_bin}" scripts/run_fixed_route_full_dense_round.py --phase all
launcher_pid="$(systemctl --user show --property=MainPID --value "${service_unit}")"
printf '%s\n' "${launcher_pid}" >"${output_root}/launcher.pid"
printf 'started service %s, PID %s\nlog: %s\n' \
  "${service_unit}" "${launcher_pid}" "${launcher_log}"
