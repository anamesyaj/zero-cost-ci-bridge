#!/usr/bin/env bash
set -u -o pipefail
umask 077

SOURCE_DIR="${1:-${GITHUB_WORKSPACE}/workload}"
ROOT="${RUNNER_TEMP}/transient-certification-${GITHUB_RUN_ID:-manual}-${GITHUB_RUN_ATTEMPT:-1}"
LOG_DIR="${ROOT}/private-logs"
DB_START_ATTEMPTED=0

status() {
  printf '%s: %s\n' "$1" "$2"
}

cleanup() {
  set +e
  local rc=0

  if [[ "${DB_START_ATTEMPTED}" -eq 1 && -x "${SOURCE_DIR}/node_modules/.bin/supabase" ]]; then
    (
      cd "${SOURCE_DIR}" &&
      ./node_modules/.bin/supabase stop --all --no-backup >/dev/null 2>&1
    ) || rc=1
  fi

  rm -rf "${SOURCE_DIR}" || rc=1
  rm -rf "${ROOT}" || rc=1

  if [[ ${rc} -eq 0 ]]; then
    status CLEANUP PASS
  else
    status CLEANUP FAIL
  fi

  return "${rc}"
}

finish() {
  local original_rc=$?
  trap - EXIT
  set +e
  cleanup
  local cleanup_rc=$?

  if [[ ${original_rc} -eq 0 && ${cleanup_rc} -eq 0 ]]; then
    status CERTIFICATION PASS
    exit 0
  fi

  status CERTIFICATION FAIL
  exit 1
}

trap finish EXIT
mkdir -p "${LOG_DIR}"

if [[ ! -d "${SOURCE_DIR}/.git" || ! -f "${SOURCE_DIR}/package.json" ]]; then
  status SOURCE_CONTEXT FAIL
  exit 1
fi
status SOURCE_CONTEXT PASS

run_phase() {
  local phase="$1"
  shift
  local log_name
  log_name="$(printf '%s' "${phase}" | tr '[:upper:]' '[:lower:]')"

  if (
    cd "${SOURCE_DIR}" &&
    "$@"
  ) >"${LOG_DIR}/${log_name}.log" 2>&1; then
    status "${phase}" PASS
    return 0
  fi

  status "${phase}" FAIL
  return 1
}

run_phase DEPENDENCIES npm ci || exit 1
run_phase LINT npm run lint || exit 1
run_phase TESTS npm test || exit 1
run_phase BUILD npm run build || exit 1

if (
  cd "${SOURCE_DIR}"
  expected_version="$(node -p 'require("./package.json").devDependencies?.supabase || ""')"
  actual_version="$(./node_modules/.bin/supabase --version)"
  [[ "${expected_version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
  [[ "${actual_version}" == "${expected_version}" ]]
  ./node_modules/.bin/supabase db start --help >/dev/null
  ./node_modules/.bin/supabase test db --help >/dev/null
) >"${LOG_DIR}/database-toolchain.log" 2>&1; then
  status DATABASE_TOOLCHAIN PASS
else
  status DATABASE_TOOLCHAIN FAIL
  exit 1
fi

for forbidden_name in \
  SUPABASE_ACCESS_TOKEN \
  SUPABASE_DB_PASSWORD \
  SUPABASE_PROJECT_ID \
  SUPABASE_SERVICE_ROLE_KEY \
  SUPABASE_SECRET_KEY; do
  if [[ -n "${!forbidden_name-}" ]]; then
    status CREDENTIAL_GUARD FAIL
    exit 1
  fi
done
status CREDENTIAL_GUARD PASS

DB_START_ATTEMPTED=1
run_phase DATABASE_START ./node_modules/.bin/supabase db start || exit 1
run_phase DATABASE_CERTIFICATION ./node_modules/.bin/supabase test db || exit 1
