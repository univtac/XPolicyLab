#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
XPL_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
UNIVTAC_ROOT="$(cd "${XPL_ROOT}/../.." && pwd)"
: "${UNIVTAC_ACT_CKPT_DIR:?Set UNIVTAC_ACT_CKPT_DIR to an ACT checkpoint directory}"
PORT="${1:-19001}"
HOST="${2:-127.0.0.1}"
ACT_DEVICE="${UNIVTAC_ACT_DEVICE:-cpu}"

exec env PYTHONPATH="${UNIVTAC_ROOT}:${XPL_ROOT}/..:${XPL_ROOT}:${PYTHONPATH:-}" \
  UNIVTAC_ROOT="${UNIVTAC_ROOT}" \
  UNIVTAC_ACT_CKPT_DIR="${UNIVTAC_ACT_CKPT_DIR}" \
  python "${XPL_ROOT}/setup_policy_server.py" \
    --config_path "${SCRIPT_DIR}/deploy.yml" \
    --overrides "port=${PORT}" "host=${HOST}" "device=${ACT_DEVICE}" "ckpt_dir=${UNIVTAC_ACT_CKPT_DIR}"
