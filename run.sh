#!/usr/bin/env bash

set -u

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
LOCK_FILE="${LOCK_FILE:-/tmp/odds_v2_run.lock}"

if [[ -f "${ROOT_DIR}/.env" ]]; then
	set -a
	# shellcheck disable=SC1091
	. "${ROOT_DIR}/.env"
	set +a
fi

# Defaults: skip doubles
export BETCLIC_SKIP_DOUBLES="${BETCLIC_SKIP_DOUBLES:-1}"
export BETFAN_SKIP_DOUBLES="${BETFAN_SKIP_DOUBLES:-1}"
export IFORBET_SKIP_DOUBLES="${IFORBET_SKIP_DOUBLES:-1}"
export ETOTO_SKIP_DOUBLES="${ETOTO_SKIP_DOUBLES:-1}"
export TOTALBET_SKIP_DOUBLES="${TOTALBET_SKIP_DOUBLES:-1}"
export LVBET_SKIP_DOUBLES="${LVBET_SKIP_DOUBLES:-1}"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
	printf '%s\n' "[ERROR] Another run.sh process is already running." >&2
	exit 1
fi

mkdir -p "${ROOT_DIR}/logs"

cd "${ROOT_DIR}" || exit 1
"$PYTHON_BIN" -m src.runner
