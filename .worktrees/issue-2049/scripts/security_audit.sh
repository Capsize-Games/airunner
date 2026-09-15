#!/usr/bin/env bash
set -euo pipefail

# Repeatable, rg-based security audit for airunner.
# Produces a markdown report you can triage into GitHub issues.
#
# Usage:
#   ./scripts/security_audit.sh
#   ./scripts/security_audit.sh --out /tmp/airunner-security-audit.md
#   ./scripts/security_audit.sh --include-deps   # (NOT recommended; can be huge)
#
# Requirements:
#   - ripgrep (rg)

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

out=""
include_deps=0
max_columns=240

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      out="${2:-}"
      if [[ -z "$out" ]]; then
        echo "Missing path after --out" >&2
        exit 2
      fi
      shift 2
      ;;
    --include-deps)
      include_deps=1
      shift
      ;;
    --max-columns)
      max_columns="${2:-}"
      if [[ -z "$max_columns" ]]; then
        echo "Missing number after --max-columns" >&2
        exit 2
      fi
      if ! [[ "$max_columns" =~ ^[0-9]+$ ]]; then
        echo "--max-columns must be an integer" >&2
        exit 2
      fi
      shift 2
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 2
      ;;
  esac
done
if [[ "${1:-}" == "--out" ]]; then
  out="${2:-}"
  if [[ -z "$out" ]]; then
    echo "Missing path after --out" >&2
    exit 2
  fi
fi

if ! command -v rg >/dev/null 2>&1; then
  echo "rg is required (ripgrep). Install it and re-run." >&2
  exit 2
fi

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
if [[ -z "$out" ]]; then
  mkdir -p "$repo_root/reports"
  out="$repo_root/reports/security-audit-${stamp}.md"
fi

body_tmp="$(mktemp)"
summary_tmp="$(mktemp)"
current_section_title=""

cleanup() {
  rm -f "$body_tmp" "$summary_tmp" 2>/dev/null || true
}
trap cleanup EXIT

# Keep output stable/diffable.
write_header() {
  {
    echo "# airunner security audit report"
    echo
    echo "- Generated: ${stamp}"
    echo "- Repo root: ${repo_root}"
    echo "- Tooling: ripgrep (rg)"
    echo "- Output: max_columns=${max_columns} (preview truncation enabled)"
    echo
    echo "This report is a *candidate findings* list designed for fast AI triage."
    echo "Counts are approximate; open the referenced files to confirm reachability and severity."
    echo
  } >"$out"
}

write_summary() {
  {
    echo "## AI triage summary"
    echo
    echo "Sorted by priority, then match count."
    echo
    echo "| Priority | Section | Check | Matches | Files |"
    echo "|---|---|---|---:|---:|"
  } >>"$out"

  # summary_tmp format: priority<TAB>section<TAB>title<TAB>matches<TAB>files
  # Sort key: prio_num asc, matches desc
  awk -F'\t' '
    function prio_num(p) {
      if (p == "P0") return 0;
      if (p == "P1") return 1;
      if (p == "P2") return 2;
      if (p == "P3") return 3;
      return 9;
    }
    { print prio_num($1) "\t" $4 "\t" $1 "\t" $2 "\t" $3 "\t" $4 "\t" $5 }
  ' "$summary_tmp" \
    | sort -t$'\t' -k1,1n -k2,2nr \
    | awk -F$'\t' '{ printf "| %s | %s | %s | %s | %s |\n", $3, $4, $5, $6, $7 }' \
    >>"$out"

  echo >>"$out"
}

section() {
  local title="$1"
  current_section_title="$title"
  {
    echo
    echo "## ${title}"
    echo
  } >>"$body_tmp"
}

run_rg() {
  local title="$1"
  local pattern="$2"
  local include_globs="$3"
  local priority="${4:-P2}"
  local preview_max_per_file="${5:-10}"

  {
    echo "### ${title}"
    echo
    echo "Pattern: \`${pattern}\`"
    echo
    echo "Priority: ${priority}"
    echo
  } >>"$body_tmp"

  # Note: we avoid --hidden by default to reduce noise.
  # Important: ordering matters. We append *excludes last* so nothing
  # (like an include glob `**/*.md`) can accidentally re-include them.
  local -a glob_flags=()
  if [[ -n "${include_globs}" ]]; then
    # allow multiple globs separated by whitespace
    read -r -a _globs <<<"${include_globs}"
    for g in "${_globs[@]}"; do
      glob_flags+=(--glob "$g")
    done
  fi

  # Always exclude generated artifacts / self-referential output.
  glob_flags+=(
    --glob '!reports/**'
    --glob '!airunner_logs/**'
    --glob '!build/**'
    --glob '!dist/**'
    --glob '!**/.git/**'
  )

  # By default, exclude dependency/vendor directories so this stays fast
  # and doesn't generate multi-hundred-MB reports.
  if [[ "$include_deps" -eq 0 ]]; then
    glob_flags+=(
      --glob '!**/.tox/**'
      --glob '!.venv/**'
      --glob '!venv/**'
      --glob '!**/site-packages/**'
      --glob '!**/dist-packages/**'
      --glob '!**/node_modules/**'
      --glob '!**/__pycache__/**'
      --glob '!**/.mypy_cache/**'
      --glob '!**/.pytest_cache/**'
      --glob '!src/**/vendor/**'
      --glob '!src/**/static/mathjax/**'
    )
  fi

  # If the pattern uses PCRE-only features (e.g. lookbehind), enable PCRE2.
  local -a pcre2_flags=()
  if [[ "$pattern" == *"(?<"* ]]; then
    pcre2_flags+=(--pcre2)
  fi

  # Add a quick, stable count so the report gives a high-level overview
  # without manual scanning.
  local match_hits=0
  local file_hits=0
  set +e
  local count_out
  count_out=$(rg -S --no-messages \
    --max-filesize 1M \
    "${pcre2_flags[@]}" \
    "${glob_flags[@]}" \
    --count-matches \
    -- "$pattern" "$repo_root" 2>/dev/null)
  local count_rc=$?
  set -e
  if [[ $count_rc -eq 0 ]]; then
    match_hits=$(printf "%s\n" "$count_out" | awk -F: '{s += $NF} END {print s+0}')
    file_hits=$(printf "%s\n" "$count_out" | awk -F: '$NF ~ /^[0-9]+$/ && $NF > 0 {c++} END {print c+0}')
  elif [[ $count_rc -eq 1 ]]; then
    match_hits=0
    file_hits=0
  else
    match_hits=0
    file_hits=0
  fi

  printf "%s\t%s\t%s\t%s\t%s\n" "$priority" "$current_section_title" "$title" "$match_hits" "$file_hits" >>"$summary_tmp"

  {
    echo "Hits: ${match_hits} matches in ${file_hits} files"
    echo
  } >>"$body_tmp"

  if [[ $match_hits -gt 0 && -n "$count_out" ]]; then
    {
      echo "Top files (by match count):"
      echo
      echo '```'
      printf "%s\n" "$count_out" | sort -t: -k2,2nr | awk 'NR<=12{print}'
      echo '```'
      echo
    } >>"$body_tmp"
  fi

  # For very high-volume checks, suppress raw match dumps to keep this report
  # readable and fast to triage.
  if [[ $match_hits -gt 250 ]]; then
    {
      echo "(match list suppressed; too many hits — use top files above, or rerun with a narrower pattern)"
      echo
    } >>"$body_tmp"
    return
  fi

  set +e
  # Safety valves:
  # - skip huge blobs (common in deps)
  # - bound output per file
  # - truncate very long lines in matches
  rg -n -S --no-messages \
    --max-filesize 1M \
    --max-count "$preview_max_per_file" \
    --max-columns "$max_columns" \
    --max-columns-preview \
    "${pcre2_flags[@]}" \
    "${glob_flags[@]}" -- "$pattern" "$repo_root" >>"$body_tmp"
  local rc=$?
  set -e

  if [[ $rc -eq 1 ]]; then
    echo "(no matches)" >>"$body_tmp"
  elif [[ $rc -ne 0 ]]; then
    echo "(rg error; exit code $rc)" >>"$body_tmp"
  fi
  echo >>"$body_tmp"
}

write_header

{
  echo "(report body below; summary is generated after scan)"
} >>"$body_tmp"

section "Remote attack surface"
run_rg "FastAPI/Uvicorn entrypoints" "FastAPI|uvicorn\.run\(|uvicorn\.Config\(|APIRouter\(" "src/**/*.py" "P2" 20
run_rg "Bind to 0.0.0.0 / listen" "0\.0\.0\.0|--host\s+0\.0\.0\.0|host=\"0\.0\.0\.0\"" "src/**/*.py Dockerfile docker-compose*.yml" "P1" 20
run_rg "Auth middleware / API key" "x-api-key|authorization\b|AIRUNNER_API_KEY|api_key_auth|compare_digest" "src/**/*.py" "P1" 20
run_rg "CORS configuration" "CORSMiddleware|allow_origins|allow_credentials" "src/**/*.py" "P2" 10
run_rg "Docs/OpenAPI endpoints" "docs_url|redoc_url|openapi\.json|/docs|/redoc" "src/**/*.py" "P3" 10

section "SSRF / outbound HTTP"
run_rg "httpx/requests usage" "\bhttpx\.|\brequests\." "src/**/*.py" "P3" 2
run_rg "Missing timeouts (requests)" "requests\.(get|post|put|delete|patch)\(" "src/**/*.py" "P3" 3
run_rg "TLS verification disabled" "verify\s*=\s*False|CERT_NONE|_create_unverified_context" "src/**/*.py" "P0" 10
run_rg "User-controlled URL indicators" "url\s*=|target_url|callback_url|webhook|openrouter|proxy" "src/**/*.py" "P2" 1

section "RCE / injection primitives"
run_rg "Dynamic code execution" "(?<!\.)\b(exec|eval)\(" "src/**/*.py" "P0" 20
run_rg "shell=True usage" "shell\s*=\s*True" "src/**/*.py" "P0" 20
run_rg "subprocess.Popen usage" "subprocess\.Popen\(" "src/**/*.py" "P2" 10
run_rg "os.system usage" "os\.system\(" "src/**/*.py" "P1" 10
run_rg "Templating injection" "jinja2|Template\(" "src/**/*.py" "P2" 10
run_rg "Unsafe deserialization" "pickle\.loads|pickle\.load|yaml\.load\(|jsonpickle|marshal\.loads|dill\.loads|cloudpickle" "src/**/*.py" "P1" 10

section "File system / path traversal"
run_rg "User-supplied paths" "open\(|Path\(|os\.path\.join\(|send_file|FileResponse" "src/**/*.py" "P2" 1
run_rg "Upload handling" "UploadFile|File\(|Form\(" "src/**/*.py" "P2" 2
run_rg "Zip/tar extraction" "tarfile\.|zipfile\.|extractall" "src/**/*.py" "P1" 10

section "Secrets & PII"
run_rg "Potential secrets in code" "AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|BEGIN (RSA|OPENSSH) PRIVATE KEY|Authorization:\\s*Bearer" "src/** Dockerfile docker-compose*.yml" "P0" 20
run_rg "Logging of prompts/messages" "logger\.(debug|info|warning|error)\(.*(prompt|messages|authorization|api[_-]?key|cookie)" "src/**/*.py" "P2" 5
run_rg "FacehuggerShield usage" "facehuggershield" "src/**/*.py" "P3" 3

section "GUI / frontend server (if any)"
run_rg "Frontend servers" "StaticFiles|TemplateResponse|uvicorn\.Config\(" "src/**/*.py" "P3" 10
run_rg "XSS sinks" "dangerouslySetInnerHTML|innerHTML\\s*=|new Function\(" "src/**" "P1" 10

section "Scaling & robustness"
run_rg "Rate limiting / throttling" "rate.?limit|throttle|backpressure|semaphore|queue\.Queue|max_concurrency|limit_concurrency" "src/**/*.py" "P3" 5
run_rg "Request size limits" "max_.*(size|bytes)|limit_.*(size|bytes)|client_max_body_size" "src/** Dockerfile docker-compose*.yml" "P3" 5
run_rg "Retries / circuit breakers" "retry|backoff|circuit" "src/**/*.py" "P3" 3

section "Container/runtime config"
run_rg "Docker binds / exposed ports" "ports:|EXPOSE\b|--port\b" "Dockerfile docker-compose*.yml docker-entrypoint.sh" "P2" 10
run_rg "Insecure flags" "--no-sandbox|DISABLE_SANDBOX" "Dockerfile docker-compose*.yml docker-entrypoint.sh" "P1" 10

write_summary

cat "$body_tmp" >>"$out"

{
  echo "## Next triage steps"
  echo
  echo "1) Start with P0 sections with nonzero hits."
  echo "2) For each hit, decide reachability (remote vs local) and whether inputs are attacker-controlled."
  echo "3) File GitHub issues with labels: security + one of P0/P1/P2/P3."
  echo "4) Re-run this script after fixes and compare reports to ensure deltas are understood."
  echo
  echo "Report written to: ${out}"
} >>"$out"

echo "Wrote: $out"
