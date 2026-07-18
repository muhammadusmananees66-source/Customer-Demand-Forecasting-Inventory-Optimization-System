# #!/usr/bin/env bash
# # Blocks until MLflow and Redis report healthy, or exits non-zero after a
# # bounded timeout. Used by `make test-integration-up` and CI so we never
# # hang indefinitely against a service that failed to start.
# set -euo pipefail

# TIMEOUT="${TIMEOUT:-60}"
# INTERVAL=2
# elapsed=0

# wait_for() {
#   local name="$1"
#   local check_cmd="$2"
#   elapsed=0
#   echo "Waiting for ${name}..."
#   until eval "${check_cmd}" >/dev/null 2>&1; do
#     if [ "${elapsed}" -ge "${TIMEOUT}" ]; then
#       echo "ERROR: ${name} did not become healthy within ${TIMEOUT}s" >&2
#       exit 1
#     fi
#     sleep "${INTERVAL}"
#     elapsed=$((elapsed + INTERVAL))
#   done
#   echo "${name} is healthy (${elapsed}s)"
# }

# wait_for "Redis"   "redis-cli -h localhost -p 6379 ping | grep -q PONG"
# wait_for "MLflow"  "curl -fsS http://localhost:5000/health"

# echo "All integration dependencies are ready."































#!/usr/bin/env bash
# Blocks until Redis and MLflow are reachable, or exits non-zero after a
# bounded timeout. Run as: TIMEOUT=90 ./scripts/wait_for_services.sh
#
# Design notes (read before touching this file):
# - Redis is checked with a raw bash /dev/tcp TCP probe, NOT `redis-cli`.
#   `redis-cli` only exists inside the redis:7-alpine *service container*,
#   not on the GitHub-hosted runner that executes this script. GitHub
#   Actions already blocks the job from starting until the `services:`
#   block's own --health-cmd (which DOES have redis-cli, run inside the
#   container) passes -- so by the time this script runs, Redis is already
#   protocol-level healthy. A TCP-reachability check here is sufficient
#   and correctly scoped; anything more is redundant.
# - MLflow is checked with `curl` against its real /health endpoint, not
#   just a TCP probe. MLflow is started via `docker compose up -d mlflow`
#   with no GitHub-managed health gate, so a bare open port would give a
#   false positive while SQLite backend-store init is still in progress.
set -euo pipefail

TIMEOUT="${TIMEOUT:-90}"
INTERVAL="${INTERVAL:-2}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
MLFLOW_URL="${MLFLOW_URL:-http://localhost:5000/health}"

log() { echo "[$(date -u +%H:%M:%S)] $*"; }

wait_for_tcp() {
  local name="$1" host="$2" port="$3"
  local elapsed=0
  log "Waiting for ${name} at ${host}:${port} (TCP reachability)..."
  while true; do
    if (exec 3<>"/dev/tcp/${host}/${port}") 2>/dev/null; then
      exec 3<&- 2>/dev/null || true
      exec 3>&- 2>/dev/null || true
      log "${name} is reachable (${elapsed}s elapsed)"
      return 0
    fi
    if [ "${elapsed}" -ge "${TIMEOUT}" ]; then
      log "ERROR: ${name} did not become reachable within ${TIMEOUT}s"
      return 1
    fi
    sleep "${INTERVAL}"
    elapsed=$((elapsed + INTERVAL))
  done
}

wait_for_http() {
  local name="$1" url="$2"
  local elapsed=0
  log "Waiting for ${name} at ${url} (HTTP health check)..."
  while true; do
    if curl -fsS --max-time 3 "${url}" >/dev/null 2>&1; then
      log "${name} is healthy (${elapsed}s elapsed)"
      return 0
    fi
    if [ "${elapsed}" -ge "${TIMEOUT}" ]; then
      log "ERROR: ${name} did not become healthy within ${TIMEOUT}s"
      return 1
    fi
    sleep "${INTERVAL}"
    elapsed=$((elapsed + INTERVAL))
  done
}

main() {
  local failed=0

  wait_for_tcp  "Redis"  "${REDIS_HOST}" "${REDIS_PORT}" || failed=1
  wait_for_http "MLflow" "${MLFLOW_URL}"                  || failed=1

  if [ "${failed}" -ne 0 ]; then
    log "One or more dependencies failed to become ready. Aborting."
    exit 1
  fi

  log "All integration dependencies are ready."
}

main "$@"