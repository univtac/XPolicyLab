#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
XPL_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
UNIVTAC_ROOT="$(cd "${XPL_ROOT}/../.." && pwd)"
: "${UNIVTAC_REPLAY_TRAJ:?Set UNIVTAC_REPLAY_TRAJ to an HDF5 trajectory}"
PORT="${1:-19000}"
HOST="${2:-127.0.0.1}"

overrides=("port=${PORT}" "host=${HOST}" "trajectory_path=${UNIVTAC_REPLAY_TRAJ}"
  "trajectory_start=${UNIVTAC_REPLAY_START:-0}"
  "trajectory_auto_align=${UNIVTAC_REPLAY_AUTO_ALIGN:-false}")
if [[ -n "${UNIVTAC_REPLAY_STRIDE:-}" ]]; then
  overrides+=("trajectory_stride=${UNIVTAC_REPLAY_STRIDE}")
fi
exec env PYTHONPATH="${UNIVTAC_ROOT}:${XPL_ROOT}/..:${XPL_ROOT}:${PYTHONPATH:-}" \
  UNIVTAC_REPLAY_TRAJ="${UNIVTAC_REPLAY_TRAJ}" \
  python "${XPL_ROOT}/setup_policy_server.py" \
    --config_path "${SCRIPT_DIR}/deploy.yml" \
    --overrides "${overrides[@]}"
